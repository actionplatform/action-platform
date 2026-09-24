"""A release: bump the version, write the changelog, commit, tag, push, publish — planned first, applied second."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from action_platform.core.config import Config
from action_platform.core.context import Context
from action_platform.core.exception import ReleaseError
from action_platform.core.flow.repository import Repository
from action_platform.core.release import changelog
from action_platform.core.release.components import Component, resolve
from action_platform.core.release.versioning import VersionFiles
from action_platform.logging import logger
from action_platform.core.wiring import slot, wired
from action_platform.core.files import CHANGELOG_FILE, LAST_VERSION_FILE

STABLE_BRANCHES = {"main", "master"}


@dataclass
class ReleasePlan:
    component: Component
    current: str
    next: str
    tag: str
    prerelease: bool
    changelog: str
    commits: list[str] = field(default_factory=list)
    name: str | None = None
    latest: bool = True


@slot("releaser")
class Releaser:
    def __init__(self, config: Config, repo: Repository | Path) -> None:
        self.config = config
        self.repo = repo if isinstance(repo, Repository) else Repository(repo)

    def context(
        self,
        dry_run: bool = False,
        stage: str | None = None,
        component: Component | None = None,
    ) -> Context:
        branch = self.repo.branch

        return Context(
            repo_root=self.repo.path,
            remote_url=self.repo.remote_url(),
            branch=branch,
            current_version=self.current_version(component or Component()),
            dry_run=dry_run,
            stage=stage or "",
        )

    def plan(
        self,
        level: str,
        prerelease: bool | None = None,
        component: str | None = None,
    ) -> ReleasePlan:
        """Everything the release would do, without touching the repository."""
        comp = resolve(self.config.components, component)
        ctx = self.context(component=comp)

        if not self.repo.is_clean():
            raise ReleaseError("working tree is dirty")

        if prerelease is None:
            prerelease = ctx.branch not in STABLE_BRANCHES

        next_version = self._next(ctx.current_version, level, prerelease, comp)
        tag = comp.tag(next_version)

        if next_version == ctx.current_version:
            raise ReleaseError(f"{ctx.current_version} is already the current version")

        if tag in self.repo.tags() or self.repo.remote_tag_exists(tag):
            raise ReleaseError(f"tag {tag} already exists")

        since = self.repo.latest_tag(match=comp.tag_glob)
        commits = self.repo.commits_since(since, paths=comp.pathspecs())

        return ReleasePlan(
            component=comp,
            current=ctx.current_version,
            next=next_version,
            tag=tag,
            prerelease=prerelease,
            changelog=self.config.changelog.render(next_version, commits),
            commits=commits,
        )

    def apply(self, plan: ReleasePlan) -> Context:
        """Write, commit, tag, push and publish `plan`; every step that fails undoes what came before it."""
        comp = plan.component
        ctx = self.context(component=comp)
        ctx.next_version = plan.next
        ctx.changelog = plan.changelog
        where = comp.dir(self.repo.path)
        files = VersionFiles(where, LAST_VERSION_FILE)
        had_changelog = (where / CHANGELOG_FILE).exists()

        files.write(plan.next)
        changelog.prepend(where / CHANGELOG_FILE, plan.changelog)
        synced = files.sync(plan.next)
        rel = where.relative_to(self.repo.path)
        touched = [
            str(rel / f) if str(rel) != "." else f
            for f in (LAST_VERSION_FILE, CHANGELOG_FILE, *synced)
        ]

        try:
            self.repo.add(touched)
            self.repo.commit(f"chore(release): {comp.label(plan.next)}")
        except (subprocess.CalledProcessError, OSError) as e:
            self._undo_writes(touched, had_changelog, where)
            raise ReleaseError(
                f"could not commit the release: {_stderr(e) or e}"
            ) from e

        self.repo.tag(plan.tag)

        try:
            self.repo.push()
            self.repo.push_tag(plan.tag)
        except (subprocess.CalledProcessError, OSError) as e:
            self.repo.delete_tag(plan.tag)
            self.repo.reset_hard("HEAD~1")
            raise ReleaseError(
                f"could not push the release, nothing was published: {_stderr(e) or e}"
            ) from e

        if self.config.source_host:
            self.config.source_host.create_release(
                ctx,
                tag=plan.tag,
                notes=plan.changelog,
                prerelease=plan.prerelease,
                name=plan.name,
                latest=plan.latest,
            )

        for runner in self.config.ci:
            run = runner.trigger(
                ctx, job=self.config.project_name, params={"version": plan.next}
            )
            result = runner.wait(ctx, run)

            if not result.ok:
                raise ReleaseError(f"CI {runner.name} failed")

        return ctx

    def release(
        self,
        level: str,
        dry_run: bool = False,
        prerelease: bool | None = None,
        component: str | None = None,
        name: str | None = None,
        notes: str | None = None,
        latest: bool = True,
    ) -> Context:
        """`name` titles the release on the host; `notes` (Markdown) go above the generated commit list, in CHANGELOG.md and on the host; `latest=False` publishes without marking it the latest."""
        plan = self.plan(level, prerelease=prerelease, component=component)
        plan.name = name or None
        plan.latest = latest

        if notes and notes.strip():
            plan.changelog = with_notes(plan.changelog, notes.strip())
        logger.info(
            "bump %s%s -> %s%s",
            f"{plan.component.name} " if plan.component.name else "",
            plan.current,
            plan.next,
            " (pre-release)" if plan.prerelease else "",
        )

        if dry_run:
            logger.info("dry-run enabled, skipping writes")
            ctx = self.context(dry_run=True, component=plan.component)
            ctx.next_version = plan.next
            ctx.changelog = plan.changelog

            return ctx

        return self.apply(plan)

    def current_version(self, component: Component) -> str:
        """What LAST_VERSION says — unless the repository has never been tagged for this component, in which case it is 0.0.0 whatever the file says."""
        if not self.repo.has_tag(component.tag_glob):
            return "0.0.0"

        return VersionFiles(component.dir(self.repo.path), LAST_VERSION_FILE).read()

    def next_version(
        self,
        level: str,
        prerelease: bool | None = None,
        component: str | None = None,
        branch: str | None = None,
    ) -> str:
        """The version a release would produce, without checking the tree or the tags — for previews."""
        comp = resolve(self.config.components, component)

        if prerelease is None:
            prerelease = (branch or self.repo.branch) not in STABLE_BRANCHES

        return self._next(self.current_version(comp), level, prerelease, comp)

    def _next(
        self, current: str, level: str, prerelease: bool, component: Component
    ) -> str:
        """The `[release] strategy` decides — semver unless platform.toml or a plugin says otherwise; it sees the versions already tagged for the component."""
        prefix = component.tag_prefix[:-1]
        taken = [t[len(prefix) :] for t in self.repo.tags() if t.startswith(prefix)]

        return self.config.release_strategy.next(current, level, prerelease, taken)

    def _undo_writes(
        self, touched: list[str], had_changelog: bool, where: Path
    ) -> None:
        self.repo.run(["reset", "-q", "--", *touched])
        tracked = [
            f for f in touched if had_changelog or not f.endswith(CHANGELOG_FILE)
        ]

        if tracked:
            self.repo.run(["checkout", "--", *tracked])

        if not had_changelog:
            (where / CHANGELOG_FILE).unlink(missing_ok=True)


def with_notes(entry: str, notes: str) -> str:
    """The release notes under the entry's heading, the generated commit list below them."""
    lines = entry.split("\n")
    head = next((i for i, line in enumerate(lines) if line.startswith("#")), None)

    if head is None:
        return notes + "\n\n" + entry

    return "\n".join([*lines[: head + 1], "", notes, *lines[head + 1 :]])


def build_context(
    config: Config,
    repo_root: Path,
    dry_run: bool = False,
    stage: str | None = None,
    component: Component | None = None,
) -> Context:
    return wired.releaser(config, repo_root).context(
        dry_run=dry_run, stage=stage, component=component
    )


def release(
    config: Config,
    level: str,
    repo_root: Path,
    dry_run: bool = False,
    prerelease: bool | None = None,
    component: str | None = None,
) -> Context:
    return wired.releaser(config, repo_root).release(
        level, dry_run=dry_run, prerelease=prerelease, component=component
    )


def _stderr(e: Exception) -> str:
    return getattr(e, "stderr", "") or ""
