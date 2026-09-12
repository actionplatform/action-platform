"""Release: bump, changelog, tag, publish."""

from __future__ import annotations

from pathlib import Path

from action_platform.core.config import Config
from action_platform.core.context import Context
from action_platform.core.exception import ReleaseError
from action_platform.core.flow import git
from action_platform.core.release import changelog, versioning
from action_platform.logging import logger
from action_platform.settings import settings


def build_context(
    config: Config, repo_root: Path, dry_run: bool = False, stage: str | None = None
) -> Context:
    branch = git.current_branch(cwd=repo_root)

    return Context(
        repo_root=repo_root,
        remote_url=git.remote_url(cwd=repo_root),
        branch=branch,
        current_version=versioning.read(repo_root / settings.LAST_VERSION_FILE),
        dry_run=dry_run,
        stage=stage or ("prod" if branch in {"main", "master"} else "dev"),
    )


def _next_version(current: str, level: str, prerelease: bool, repo_root: Path) -> str:
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

    return versioning.next_rc(target, git.tags(cwd=repo_root))


def release(
    config: Config,
    level: str,
    repo_root: Path,
    dry_run: bool = False,
    prerelease: bool | None = None,
) -> Context:
    ctx = build_context(config, repo_root, dry_run=dry_run)

    if not git.is_clean(cwd=repo_root):
        raise ReleaseError("working tree is dirty")

    if prerelease is None:
        prerelease = ctx.branch not in {"main", "master"}

    ctx.next_version = _next_version(ctx.current_version, level, prerelease, repo_root)
    tag = f"v{ctx.next_version}"

    if ctx.next_version == ctx.current_version:
        raise ReleaseError(f"{ctx.current_version} is already the current version")

    if tag in git.tags(cwd=repo_root) or git.remote_tag_exists(tag, cwd=repo_root):
        raise ReleaseError(f"tag {tag} already exists")

    logger.info(
        "bump %s -> %s%s",
        ctx.current_version,
        ctx.next_version,
        " (pre-release)" if prerelease else "",
    )

    commits = git.commits_since(git.latest_tag(cwd=repo_root), cwd=repo_root)
    ctx.changelog = changelog.render(ctx.next_version, commits)

    if dry_run:
        logger.info("dry-run enabled, skipping writes")
        return ctx

    versioning.write(repo_root / settings.LAST_VERSION_FILE, ctx.next_version)
    changelog.prepend(repo_root / settings.CHANGELOG_FILE, ctx.changelog)
    synced = versioning.sync_files(repo_root, ctx.next_version)

    git.add(
        [settings.LAST_VERSION_FILE, settings.CHANGELOG_FILE, *synced], cwd=repo_root
    )
    git.commit(f"chore(release): {ctx.next_version}", cwd=repo_root)
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
