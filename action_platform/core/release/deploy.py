"""Deploy, rollback, diagnose, destroy against the [deploy] targets of one repository."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from action_platform.abc.deploy_target import DeployTarget
from action_platform.core.config import Config
from action_platform.core.context import Context, DeployResult, Diagnosis
from action_platform.core.exception import DeployError
from action_platform.core.flow.repository import Repository
from action_platform.core.wiring import slot, wired
from action_platform.logging import logger


@slot("deployer")
class Deployer:
    def __init__(
        self,
        config: Config,
        repo: Repository | Path,
        identity: Callable[[str], str] | None = None,
    ) -> None:
        self.config = config
        self.repo = repo if isinstance(repo, Repository) else Repository(repo)
        self.identity = identity

    def targets(self, name: str | None = None) -> list[DeployTarget]:
        targets = (
            self.config.deploy
            if name is None
            else [t for t in self.config.deploy if t.name == name]
        )

        if not targets:
            raise DeployError(
                f"no deploy target configured (filter={name!r}) — "
                "run `action-platform cloud set <cloud>`"
            )

        return targets

    def _context(self, dry_run: bool = False, stage: str | None = None) -> Context:
        ctx = wired.releaser(self.config, self.repo).context(
            dry_run=dry_run, stage=stage
        )
        ctx.next_version = ctx.current_version
        ctx.identity = self.identity

        return ctx

    def deploy(
        self, target: str | None = None, dry_run: bool = False, stage: str | None = None
    ) -> list[DeployResult]:
        ctx = self._context(dry_run=dry_run, stage=stage)
        results: list[DeployResult] = []

        for t in self.targets(target):
            logger.info(
                "deploy target=%s stage=%s version=%s",
                t.name,
                ctx.stage,
                ctx.next_version,
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
        self,
        target: str | None = None,
        to_version: str | None = None,
        stage: str | None = None,
    ) -> None:
        ctx = self._context(stage=stage)

        for t in self.targets(target):
            logger.info(
                "rollback target=%s stage=%s to=%s", t.name, ctx.stage, to_version
            )
            t.preflight(ctx)
            t.rollback(ctx, to_version)

    def diagnose(
        self, target: str | None = None, stage: str | None = None
    ) -> list[Diagnosis]:
        ctx = self._context(stage=stage)

        return [t.diagnose(ctx) for t in self.targets(target)]

    def destroy(self, target: str | None = None, stage: str | None = None) -> None:
        ctx = self._context(stage=stage)

        for t in self.targets(target):
            logger.info("delete target=%s stage=%s", t.name, ctx.stage)
            t.preflight(ctx)
            t.delete(ctx)


def deploy(
    config: Config,
    target_name: str | None,
    repo_root: Path,
    dry_run: bool = False,
    stage: str | None = None,
) -> list[DeployResult]:
    return wired.deployer(config, repo_root).deploy(
        target_name, dry_run=dry_run, stage=stage
    )


def rollback(
    config: Config,
    target_name: str | None,
    repo_root: Path,
    to_version: str | None = None,
    stage: str | None = None,
) -> None:
    wired.deployer(config, repo_root).rollback(
        target_name, to_version=to_version, stage=stage
    )


def diagnose(
    config: Config, target_name: str | None, repo_root: Path, stage: str | None = None
) -> list[Diagnosis]:
    return wired.deployer(config, repo_root).diagnose(target_name, stage=stage)


def destroy(
    config: Config, target_name: str | None, repo_root: Path, stage: str | None = None
) -> None:
    wired.deployer(config, repo_root).destroy(target_name, stage=stage)
