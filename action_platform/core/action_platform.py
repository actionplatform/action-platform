"""The facade the CLI, the MCP server and the API call: one project, its configuration, its git clone."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from action_platform.core.wiring import wired
from action_platform.core.config import Config
from action_platform.core.context import Context, DeployResult, Diagnosis
from action_platform.core.flow.repository import Repository
from action_platform.core.flow.workflow import GitFlow
from action_platform.core.release.deploy import Deployer
from action_platform.core.release.release import ReleasePlan, Releaser
from action_platform.plugins import registry


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
        identity: signs a short-lived OIDC token for an audience — the hosted
            platform's issuer for a deploy it runs, the platform the CLI is
            logged in to otherwise; None on a plain machine.
        env: what the platform knows and the repository does not — settings a
            deploy target may read from `ctx.env` (`AP_APP`, a cloud's proxy
            url) instead of platform.toml.
    """

    def __init__(
        self,
        config: Config | None = None,
        repo_root: Path | None = None,
        identity: Callable[[str], str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.config = config or Config()
        self.repo = Repository(repo_root or Path.cwd())
        self.identity = identity
        self.env = dict(env or {})

    @property
    def repo_root(self) -> Path:
        return self.repo.path

    @property
    def releaser(self) -> Releaser:
        return wired.releaser(self.config, self.repo)

    @property
    def deployer(self) -> Deployer:
        return wired.deployer(
            self.config, self.repo, identity=self.identity, env=self.env
        )

    @property
    def flow(self) -> GitFlow:
        return wired.gitflow(self.repo)

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
        ctx = self.releaser.release(
            level, dry_run=dry_run, prerelease=prerelease, component=component
        )

        if not dry_run:
            registry.installed().after_release(ctx)

        return ctx

    def deploy(
        self, target: str | None = None, dry_run: bool = False, stage: str | None = None
    ) -> list[DeployResult]:
        results = self.deployer.deploy(target, dry_run=dry_run, stage=stage)

        if not dry_run:
            registry.installed().after_deploy(results)

        return results

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
