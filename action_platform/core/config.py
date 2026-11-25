"""Action Platform Config."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

import tomllib

from action_platform.abc.changelog_renderer import ChangelogRenderer
from action_platform.abc.ci_runner import CIRunner
from action_platform.abc.deploy_target import DeployTarget
from action_platform.abc.release_strategy import ReleaseStrategy
from action_platform.abc.source_host import SourceHost
from action_platform.core import module
from action_platform.core.exception import ConfigError
from action_platform.core.flow.protection import ProtectionSpec
from action_platform.core.release import strategies
from action_platform.core.release.components import parse as parse_components
from action_platform.core.scopes import ScopeSpec, parse_scopes
from action_platform.core.targets import TargetSpec, parse_targets
from action_platform.options import SourceTokens
from action_platform.providers.ci.factory import build_ci_runner
from action_platform.providers.deploy import BUILTIN_DEPLOY_TARGETS
from action_platform.providers.deploy.dispatched import (
    DispatchedTarget,
    UnverifiedTarget,
)
from action_platform.providers.source import build_source_host


class Config:
    """
    Import:
        from action_platform import Config
        from action_platform.providers import SourceGithub

    Example:
        config = Config(source_host=SourceGithub(repo="actionplatform/my-project"))

    CI runners and deploy targets come from `platform.toml` through the
    `action_platform.ci_runner` / `action_platform.deploy_target` entry-point groups.

    Args:
        source_host (SourceHost): provider for tag/release/PR.
        ci (list[CIRunner]): pipelines triggered on release.
        deploy (list[DeployTarget]): deploy targets.
        project_name (str): project name.
        language (str): primary stack.
    """

    def __init__(
        self,
        source_host: SourceHost | None = None,
        ci: list[CIRunner] | None = None,
        deploy: list[DeployTarget] | None = None,
        project_name: str = "",
        language: str = "",
    ) -> None:
        self.source_host = source_host
        self.ci = ci or []
        self.project_name = project_name
        self.language = language
        self._deploy = deploy
        self._deploy_spec: dict = {}
        self._components_spec: dict = {}
        self._release_spec: dict = {}
        self._scopes_spec: list = []
        self._gitflow_spec: dict = {}

    @property
    def components(self):
        """Release components declared in platform.toml (root included under "")."""
        return parse_components(self._components_spec)

    @property
    def targets(self) -> list[TargetSpec]:
        """Every deploy target platform.toml declares, whoever runs it."""
        return parse_targets(self._deploy_spec)

    @property
    def protection(self) -> ProtectionSpec:
        """`[gitflow.protection]`: whether the code host enforces git-flow, and on which branches."""
        return ProtectionSpec.parse(self._gitflow_spec)

    @property
    def scopes(self) -> list[ScopeSpec]:
        """Where releases are deployed: `[[scopes]]`; none means the repository does not deploy."""
        return parse_scopes({"scopes": self._scopes_spec})

    def scope(self, name: str) -> ScopeSpec:
        spec = next((s for s in self.scopes if s.name == name), None)

        if spec is None:
            raise ConfigError(
                f"no scope named {name!r} (scopes: {', '.join(s.name for s in self.scopes) or 'none'})"
            )

        return spec

    @property
    def deploy(self) -> list[DeployTarget]:
        """The targets the platform runs itself, resolved lazily: loading platform.toml never needs a provider installed."""
        if self._deploy is None:
            self._deploy = _build_deploy_targets(self._deploy_spec)

        return self._deploy

    def runnable(
        self, name: str | None = None, stage: str | None = None
    ) -> list[DeployTarget]:
        """The platform's own and the dispatched targets named `name` and serving `stage`, chosen on their declarations before any is built: a target outside the selection never resolves its provider or runner."""

        def wanted(spec: TargetSpec) -> bool:
            return (name is None or spec.name == name) and (
                stage is None or spec.serves(stage)
            )

        specs = {s.name: s for s in self.targets}

        if self._deploy is None:
            own = [_build_target(s) for s in specs.values() if s.platform and wanted(s)]
        else:
            own = [
                t
                for t in self._deploy
                if (
                    wanted(specs[t.name]) if t.name in specs else name in (None, t.name)
                )
            ]

        return own + self.dispatched(wanted)

    def dispatched(
        self, keep: Callable[[TargetSpec], bool] | None = None
    ) -> list[DeployTarget]:
        """The targets a CI runs for the platform — `run_by = "github_actions"`, a Jenkins job with `observe = false` and the like — each wrapped so a deploy starts the run and follows it; `keep` picks which before they are built."""
        return [
            DispatchedTarget(
                _dispatched_inner(spec),
                self._runner_for(spec),
                spec.job if spec.run_by == "jenkins" else spec.workflow,
                str(spec.options.get("registry") or ""),
                version_parameter=spec.version_parameter
                if spec.run_by == "jenkins"
                else "",
            )
            for spec in self.targets
            if spec.dispatched and (keep is None or keep(spec))
        ]

    def _runner_for(self, spec: TargetSpec) -> CIRunner:
        """A server of its own (Jenkins) comes from `ci`, connected with its own credentials; an embedded CI from the source host."""
        if spec.run_by == "jenkins":
            runner = next((r for r in self.ci if r.name == "jenkins"), None)

            if runner is None:
                raise ConfigError(
                    f"{spec.name} is run by jenkins, but no Jenkins server is connected to the app"
                )

            return runner

        if self.source_host is None:
            raise ConfigError(
                f"{spec.name} is run by {spec.run_by}, but platform.toml names no source host"
            )

        return build_ci_runner(
            spec.run_by,
            repo=self.source_host.repo,
            token=self.source_host.token,
            base_url=getattr(self.source_host, "api", None)
            if spec.run_by == "github_actions"
            else getattr(self.source_host, "web", None),
            username=getattr(self.source_host, "username", None),
        )

    def runs_with(self, name: str) -> list[TargetSpec]:
        """The other targets one dispatch of target `name` deploys: Jenkins targets started on the same job that take no stage parameter share its build."""
        spec = next((t for t in self.targets if t.name == name), None)

        if spec is None or spec.run_by != "jenkins" or not spec.dispatched:
            return []

        if not spec.job or spec.stage_parameter:
            return []

        return [
            t
            for t in self.targets
            if t.name != spec.name
            and t.run_by == "jenkins"
            and t.dispatched
            and t.job == spec.job
            and not t.stage_parameter
        ]

    def provides(self, kind: str) -> bool:
        """Whether a provider for deploy target `kind` is installed."""
        return kind in _providers()

    def target(self, name: str) -> DeployTarget:
        """A provider for target `name`, whoever runs it — for verify and url."""
        spec = next((t for t in self.targets if t.name == name), None)

        if spec is None:
            raise ConfigError(f"no deploy target named {name!r}")

        return _build_target(spec)

    @property
    def release_strategy(self) -> ReleaseStrategy:
        """`[release] strategy`, semver unless platform.toml or a plugin says otherwise."""
        return strategies.strategy(self._release_spec.get("strategy") or "semver")

    @property
    def changelog(self) -> ChangelogRenderer:
        """`[release] changelog`, conventional unless platform.toml or a plugin says otherwise."""
        return strategies.renderer(
            self._release_spec.get("changelog") or "conventional"
        )

    @classmethod
    def from_toml(cls, path: Path, tokens: SourceTokens | None = None) -> "Config":
        if not path.exists():
            raise ConfigError(f"platform.toml not found at {path}")

        return cls.from_dict(tomllib.loads(path.read_text()), tokens=tokens)

    @classmethod
    def from_dict(cls, data: dict, tokens: SourceTokens | None = None) -> "Config":
        """The same tables platform.toml holds, from wherever they were kept — the file, or the hosted platform's database.

        `tokens` are the code-host credentials the source host gets; None
        means the ones this machine's environment holds (`SourceTokens.from_env`).
        """
        project = data.get("project", {})
        tokens = SourceTokens.from_env(os.environ) if tokens is None else tokens

        config = cls(
            source_host=_build_source_host(data.get("source_host", {}), tokens),
            project_name=project.get("name", ""),
            language=project.get("language", ""),
        )
        config._deploy_spec = data.get("deploy", {})
        config._components_spec = data.get("components", {})
        config._release_spec = data.get("release", {})
        config._scopes_spec = data.get("scopes", [])
        config._gitflow_spec = data.get("gitflow", {})

        return config


def _build_source_host(cfg: dict, tokens: SourceTokens) -> SourceHost | None:
    kind = cfg.get("kind")

    if not kind:
        return None

    return build_source_host(
        kind,
        cfg.get("repo", ""),
        cfg.get("base_url"),
        token=tokens.token(kind),
        username=tokens.username(kind),
    )


def _providers() -> dict[str, type]:
    return {**BUILTIN_DEPLOY_TARGETS, **module.load_deploy_targets()}


def _build_target(spec: TargetSpec) -> DeployTarget:
    providers = _providers()

    if spec.kind not in providers:
        installed = ", ".join(sorted(providers)) or "none"
        raise ConfigError(
            f"no provider installed for deploy target {spec.kind!r} (installed: {installed})"
        )

    target = providers[spec.kind](**spec.options)

    if spec.name != spec.kind:
        target.name = spec.name

    return target


def _dispatched_inner(spec: TargetSpec) -> DeployTarget:
    """The provider a dispatched target verifies with; a job that takes the release as a parameter is started and followed without one."""
    if spec.version_parameter and spec.kind not in _providers():
        return UnverifiedTarget(spec.name)

    return _build_target(spec)


def _build_deploy_targets(cfg: dict) -> list[DeployTarget]:
    """The `run_by = "platform"` targets of `[deploy]`, each resolved through the built-in kinds and the `action_platform.deploy_target` entry-point group; the other keys of a target go to its provider."""
    return [_build_target(spec) for spec in parse_targets(cfg) if spec.platform]
