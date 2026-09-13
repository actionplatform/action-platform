"""The facade the CLI, the MCP server and the API call: one project, its configuration, its git clone."""

from __future__ import annotations

from pathlib import Path

from action_platform.core.config import Config
from action_platform.core.context import Context, DeployResult, Diagnosis
from action_platform.core.flow.repository import Repository
from action_platform.core.flow.workflow import GitFlow
from action_platform.core.release.deploy import Deployer
from action_platform.core.release.release import ReleasePlan, Releaser


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
    """

    def __init__(
        self, config: Config | None = None, repo_root: Path | None = None
    ) -> None:
        self.config = config or Config()
        self.repo = Repository(repo_root or Path.cwd())

    @property
    def repo_root(self) -> Path:
        return self.repo.path

    @property
    def releaser(self) -> Releaser:
        return Releaser(self.config, self.repo)

    @property
    def deployer(self) -> Deployer:
        return Deployer(self.config, self.repo)

    @property
    def flow(self) -> GitFlow:
        return GitFlow(self.repo)

    def plan_release(
        self,
        level: str = "patch",
        prerelease: bool | None = None,
        component: str | None = None,
    ) -> ReleasePlan:
        return self.releaser.plan(level, prerelease=prerelease, component=component)

    def release(
        self,
        level: str = "patch",
        dry_run: bool = False,
        prerelease: bool | None = None,
        component: str | None = None,
    ) -> Context:
        return self.releaser.release(
            level, dry_run=dry_run, prerelease=prerelease, component=component
        )

    def deploy(
        self, target: str | None = None, dry_run: bool = False, stage: str | None = None
    ) -> list[DeployResult]:
        return self.deployer.deploy(target, dry_run=dry_run, stage=stage)

    def rollback(
        self,
        target: str | None = None,
        to_version: str | None = None,
        stage: str | None = None,
    ) -> None:
        self.deployer.rollback(target, to_version=to_version, stage=stage)

    def diagnose(
        self, target: str | None = None, stage: str | None = None
    ) -> list[Diagnosis]:
        return self.deployer.diagnose(target, stage=stage)

    def destroy(self, target: str | None = None, stage: str | None = None) -> None:
        self.deployer.destroy(target, stage=stage)
