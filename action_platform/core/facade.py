"""The facade the CLI, the MCP server and the API call: one project, its configuration, its git clone."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from action_platform.core.wiring import Wiring
from action_platform.core.config import Config
from action_platform.core.context import Check, Context, DeployResult, Diagnosis
from action_platform.core.exception import ConfigError
from action_platform.core.flow.repository import Repository
from action_platform.core.flow.workflow import GitFlow
from action_platform.core.release.deploy import Deployer
from action_platform.core.release.readiness import Readiness
from action_platform.core.release.release import ReleasePlan, Releaser
from action_platform.core import extensions


class ActionPlatform:
    """
    Import:
        from action_platform import ActionPlatform, Config

    Example:
        tool = ActionPlatform(config=Config(...))
        tool.release("patch")
        tool.deploy()

    Args:
        config (Config): configuration with injected providers — required:
            `Config.from_toml(root / "platform.toml")` for a project on disk.
        repo_root (Path): repository root. Defaults to cwd.
        identity: signs a short-lived OIDC token for an audience — the hosted
            platform's issuer for a deploy it runs, the platform the CLI is
            logged in to otherwise; None on a plain machine.
        env: what the platform knows and the repository does not — settings a
            deploy target may read from `ctx.env` (`AP_APP`, a cloud's proxy
            url) instead of platform.toml.
        wiring (Wiring): which class fills each slot; default the process's,
            where installed plugins replace slots. Every process this facade
            starts resolves through it.
    """

    def __init__(
        self,
        config: Config,
        repo_root: Path | None = None,
        identity: Callable[[str], str] | None = None,
        env: dict[str, str] | None = None,
        wiring: Wiring | None = None,
    ) -> None:
        if not isinstance(config, Config):
            raise ConfigError(
                "ActionPlatform needs a Config, e.g. Config.from_toml(root / 'platform.toml')"
            )

        self.config = config
        self.repo = Repository(repo_root or Path.cwd())
        self.identity = identity
        self.env = dict(env or {})
        self.wiring = Wiring.default() if wiring is None else wiring

    @property
    def repo_root(self) -> Path:
        return self.repo.path

    @property
    def releaser(self) -> Releaser:
        return self.wiring.releaser(self.config, self.repo)

    @property
    def deployer(self) -> Deployer:
        deployer = self.wiring.deployer(
            self.config, self.repo, identity=self.identity, env=self.env
        )
        deployer.wiring = self.wiring

        return deployer

    @property
    def readiness(self) -> Readiness:
        return self.wiring.readiness(self.config, self.repo.path, self.deployer)

    @property
    def flow(self) -> GitFlow:
        flow = self.wiring.gitflow(self.repo)
        flow.wiring = self.wiring

        return flow

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
        name: str | None = None,
        notes: str | None = None,
        latest: bool = True,
    ) -> Context:
        ctx = self.releaser.release(
            level,
            dry_run=dry_run,
            prerelease=prerelease,
            component=component,
            name=name,
            notes=notes,
            latest=latest,
        )

        if not dry_run:
            extensions.current().after_release(ctx)

        return ctx

    def deploy(
        self,
        target: str | None = None,
        dry_run: bool = False,
        stage: str | None = None,
        version: str | None = None,
    ) -> list[DeployResult]:
        results = self.deployer.deploy(
            target, dry_run=dry_run, stage=stage, version=version
        )

        if not dry_run:
            extensions.current().after_deploy(results)

        return results

    def check_readiness(
        self,
        stage: str,
        version: str | None = None,
        target: str | None = None,
        shape: str | None = None,
    ) -> list[Check]:
        return self.readiness.check(stage, version=version, target=target, shape=shape)

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
