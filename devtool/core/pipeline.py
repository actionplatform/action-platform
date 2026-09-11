"""Release + deploy orchestration."""

from __future__ import annotations

from pathlib import Path

from devtool.core import changelog, git, versioning
from devtool.core.config import Config
from devtool.core.context import Context, DeployResult
from devtool.core.exception import DeployError, ReleaseError
from devtool.logging import logger
from devtool.settings import settings


def build_context(config: Config, repo_root: Path, dry_run: bool = False) -> Context:
    return Context(
        repo_root=repo_root,
        remote_url=git.remote_url(cwd=repo_root),
        branch=git.current_branch(cwd=repo_root),
        current_version=versioning.read(repo_root / settings.LAST_VERSION_FILE),
        dry_run=dry_run,
    )


def release(config: Config, level: str, repo_root: Path, dry_run: bool = False) -> Context:
    ctx = build_context(config, repo_root, dry_run=dry_run)

    if not git.is_clean(cwd=repo_root):
        raise ReleaseError("working tree is dirty")

    ctx.next_version = versioning.bump(ctx.current_version, level)
    logger.info("bump %s -> %s", ctx.current_version, ctx.next_version)

    commits = git.commits_since(git.latest_tag(cwd=repo_root), cwd=repo_root)
    ctx.changelog = changelog.render(ctx.next_version, commits)

    if dry_run:
        logger.info("dry-run enabled, skipping writes")
        return ctx

    versioning.write(repo_root / settings.LAST_VERSION_FILE, ctx.next_version)
    (repo_root / settings.CHANGELOG_FILE).write_text(ctx.changelog)

    tag = f"v{ctx.next_version}"
    git.commit(f":bookmark: chore(release): {tag}", cwd=repo_root)
    git.create_tag(tag, tag, cwd=repo_root)
    git.push(cwd=repo_root)
    git.push_tag(tag, cwd=repo_root)

    if config.source_host:
        config.source_host.create_release(ctx, tag=tag, notes=ctx.changelog)

    for runner in config.ci:
        run = runner.trigger(ctx, job=config.project_name, params={"version": ctx.next_version})
        result = runner.wait(ctx, run)
        if not result.ok:
            raise ReleaseError(f"CI {runner.name} failed")

    return ctx


def deploy(config: Config, target_name: str | None, repo_root: Path, dry_run: bool = False) -> list[DeployResult]:
    ctx = build_context(config, repo_root, dry_run=dry_run)
    ctx.next_version = ctx.current_version

    targets = config.deploy if target_name is None else [t for t in config.deploy if t.name == target_name]
    if not targets:
        raise DeployError(f"no deploy target configured (filter={target_name!r})")

    results: list[DeployResult] = []
    for t in targets:
        logger.info("deploy target=%s version=%s", t.name, ctx.next_version)
        t.preflight(ctx)
        if dry_run:
            results.append(DeployResult(ok=True, target=t.name, version=ctx.next_version))
            continue
        results.append(t.deploy(ctx))
    return results
