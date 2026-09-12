"""ActionPlatform orchestrator."""

from __future__ import annotations

from pathlib import Path

from action_platform.core.release import deploy as deploying
from action_platform.core.release import release as releasing
from action_platform.core.config import Config
from action_platform.core.context import Context, DeployResult, Diagnosis


class ActionPlatform:
    """
    Import:
        from action_platform import ActionPlatform, Config

    Example:
        tool = ActionPlatform(config=Config(...))
        tool.release("patch")
        tool.deploy()

    Args:
        config (Config): configuration with injected providers.
        repo_root (Path): repository root. Defaults to cwd.

    Attributes:
        config (Config):
        repo_root (Path):
    """

    def __init__(
        self, config: Config | None = None, repo_root: Path | None = None
    ) -> None:
        self.config = config or Config()
        self.repo_root = repo_root or Path.cwd()

    def release(
        self,
        level: str = "patch",
        dry_run: bool = False,
        prerelease: bool | None = None,
    ) -> Context:
        return releasing.release(
            self.config, level, self.repo_root, dry_run=dry_run, prerelease=prerelease
        )

    def deploy(
        self, target: str | None = None, dry_run: bool = False, stage: str | None = None
    ) -> list[DeployResult]:
        return deploying.deploy(
            self.config, target, self.repo_root, dry_run=dry_run, stage=stage
        )

    def rollback(
        self,
        target: str | None = None,
        to_version: str | None = None,
        stage: str | None = None,
    ) -> None:
        deploying.rollback(
            self.config, target, self.repo_root, to_version=to_version, stage=stage
        )

    def diagnose(
        self, target: str | None = None, stage: str | None = None
    ) -> list[Diagnosis]:
        return deploying.diagnose(self.config, target, self.repo_root, stage=stage)

    def destroy(self, target: str | None = None, stage: str | None = None) -> None:
        deploying.destroy(self.config, target, self.repo_root, stage=stage)
