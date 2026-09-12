"""Release: bump, changelog, tag, publish."""

from __future__ import annotations

from pathlib import Path

from action_platform.core.config import Config
from action_platform.core.context import Context
from action_platform.core.exception import ReleaseError
from action_platform.core.flow import git
from action_platform.core.release import changelog, versioning
from action_platform.core.release.components import Component, resolve
from action_platform.logging import logger
from action_platform.settings import settings


def build_context(
    config: Config,
    repo_root: Path,
    dry_run: bool = False,
    stage: str | None = None,
    component: Component | None = None,
) -> Context:
    branch = git.current_branch(cwd=repo_root)
    where = (component or Component()).dir(repo_root)

    return Context(
        repo_root=repo_root,
        remote_url=git.remote_url(cwd=repo_root),
        branch=branch,
        current_version=versioning.read(where / settings.LAST_VERSION_FILE),
        dry_run=dry_run,
        stage=stage or ("prod" if branch in {"main", "master"} else "dev"),
    )


def _next_version(
    current: str, level: str, prerelease: bool, repo_root: Path, component: Component
) -> str:
    """Stable: plain bump. Pre-release: bump the stable base (or keep it when already on an rc) and add -rc.N."""
    base = versioning.strip_pre(current)
    _, _, _, pre = versioning.parse(current)

    if not prerelease:
        return versioning.bump(base, level)

    if versioning.SEMVER_RE.match(level):
        target = versioning.strip_pre(level)
    elif pre:
        target = base
    else:
        target = versioning.bump(base, level)

    # next_rc looks for "v<target>-rc.N": hand it the component's tags without the prefix.
    prefix = component.tag_prefix[:-1]  # "web/" or ""
    tags = [t[len(prefix) :] for t in git.tags(cwd=repo_root) if t.startswith(prefix)]

    return versioning.next_rc(target, tags)


def release(
    config: Config,
    level: str,
    repo_root: Path,
    dry_run: bool = False,
    prerelease: bool | None = None,
    component: str | None = None,
) -> Context:
    comp = resolve(config.components, component)
    ctx = build_context(config, repo_root, dry_run=dry_run, component=comp)
    where = comp.dir(repo_root)

    if not git.is_clean(cwd=repo_root):
        raise ReleaseError("working tree is dirty")

    if prerelease is None:
        prerelease = ctx.branch not in {"main", "master"}

    ctx.next_version = _next_version(
        ctx.current_version, level, prerelease, repo_root, comp
    )
    tag = comp.tag(ctx.next_version)

    if ctx.next_version == ctx.current_version:
        raise ReleaseError(f"{ctx.current_version} is already the current version")

    if tag in git.tags(cwd=repo_root) or git.remote_tag_exists(tag, cwd=repo_root):
        raise ReleaseError(f"tag {tag} already exists")

    logger.info(
        "bump %s%s -> %s%s",
        f"{comp.name} " if comp.name else "",
        ctx.current_version,
        ctx.next_version,
        " (pre-release)" if prerelease else "",
    )

    since = git.latest_tag(cwd=repo_root, match=comp.tag_glob)
    commits = git.commits_since(since, cwd=repo_root, paths=comp.pathspecs())
    ctx.changelog = changelog.render(ctx.next_version, commits)

    if dry_run:
        logger.info("dry-run enabled, skipping writes")
        return ctx

    versioning.write(where / settings.LAST_VERSION_FILE, ctx.next_version)
    changelog.prepend(where / settings.CHANGELOG_FILE, ctx.changelog)
    synced = versioning.sync_files(where, ctx.next_version)
    rel = where.relative_to(repo_root)
    touched = [
        str(rel / f) if str(rel) != "." else f
        for f in (settings.LAST_VERSION_FILE, settings.CHANGELOG_FILE, *synced)
    ]

    git.add(touched, cwd=repo_root)
    git.commit(f"chore(release): {comp.label(ctx.next_version)}", cwd=repo_root)
    git.create_tag(tag, tag, cwd=repo_root)
    git.push(cwd=repo_root)
    git.push_tag(tag, cwd=repo_root)

    if config.source_host:
        config.source_host.create_release(
            ctx, tag=tag, notes=ctx.changelog, prerelease=prerelease
        )

    for runner in config.ci:
        run = runner.trigger(
            ctx, job=config.project_name, params={"version": ctx.next_version}
        )
        result = runner.wait(ctx, run)

        if not result.ok:
            raise ReleaseError(f"CI {runner.name} failed")

    return ctx
