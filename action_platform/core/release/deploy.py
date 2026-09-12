"""Deploy, rollback, diagnose, destroy against the [deploy] targets."""

from __future__ import annotations

from pathlib import Path

from action_platform.core.config import Config
from action_platform.core.context import DeployResult, Diagnosis
from action_platform.core.exception import DeployError
from action_platform.core.release.release import build_context
from action_platform.logging import logger


def _targets(config: Config, target_name: str | None):
    targets = (
        config.deploy
        if target_name is None
        else [t for t in config.deploy if t.name == target_name]
    )

    if not targets:
        raise DeployError(
            f"no deploy target configured (filter={target_name!r}) — "
            "run `action-platform cloud set <cloud>`"
        )

    return targets


def deploy(
    config: Config,
    target_name: str | None,
    repo_root: Path,
    dry_run: bool = False,
    stage: str | None = None,
) -> list[DeployResult]:
    ctx = build_context(config, repo_root, dry_run=dry_run, stage=stage)
    ctx.next_version = ctx.current_version

    results: list[DeployResult] = []

    for t in _targets(config, target_name):
        logger.info(
            "deploy target=%s stage=%s version=%s", t.name, ctx.stage, ctx.next_version
        )
        t.preflight(ctx)

        if dry_run:
            results.append(
                DeployResult(ok=True, target=t.name, version=ctx.next_version)
            )
            continue

        results.append(t.deploy(ctx))

    return results


def rollback(
    config: Config,
    target_name: str | None,
    repo_root: Path,
    to_version: str | None = None,
    stage: str | None = None,
) -> None:
    ctx = build_context(config, repo_root, stage=stage)

    for t in _targets(config, target_name):
        logger.info("rollback target=%s stage=%s to=%s", t.name, ctx.stage, to_version)
        t.preflight(ctx)
        t.rollback(ctx, to_version)


def diagnose(
    config: Config, target_name: str | None, repo_root: Path, stage: str | None = None
) -> list[Diagnosis]:
    ctx = build_context(config, repo_root, stage=stage)
    ctx.next_version = ctx.current_version

    return [t.diagnose(ctx) for t in _targets(config, target_name)]


def destroy(
    config: Config, target_name: str | None, repo_root: Path, stage: str | None = None
) -> None:
    ctx = build_context(config, repo_root, stage=stage)

    for t in _targets(config, target_name):
        logger.info("delete target=%s stage=%s", t.name, ctx.stage)
        t.preflight(ctx)
        t.delete(ctx)
