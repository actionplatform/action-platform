"""Action Platform Config."""

from __future__ import annotations

import os
from pathlib import Path

import tomllib

from action_platform.abc.changelog_renderer import ChangelogRenderer
from action_platform.abc.ci_runner import CIRunner
from action_platform.abc.deploy_target import DeployTarget
from action_platform.abc.release_strategy import ReleaseStrategy
from action_platform.abc.source_host import SourceHost
from action_platform.core import module
from action_platform.core.exception import ConfigError
from action_platform.core.release import strategies
from action_platform.core.release.components import parse as parse_components
from action_platform.core.scopes import ScopeSpec, parse_scopes
from action_platform.core.targets import TargetSpec, parse_targets
from action_platform.options import SourceTokens
from action_platform.providers.ci.factory import build_ci_runner
from action_platform.providers.deploy import BUILTIN_DEPLOY_TARGETS
from action_platform.providers.deploy.dispatched import DispatchedTarget
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

    @property
    def components(self):
        """Release components declared in platform.toml (root included under "")."""
        return parse_components(self._components_spec)

    @property
    def targets(self) -> list[TargetSpec]:
        """Every deploy target platform.toml declares, whoever runs it."""
        return parse_targets(self._deploy_spec)

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

    def dispatched(self) -> list[DeployTarget]:
        """The targets a CI of the source host runs for the platform — `run_by = "github_actions"` and the like — each wrapped so a deploy starts the workflow and follows the run."""
        specs = [t for t in self.targets if t.dispatched]

        if not specs:
            return []

        if self.source_host is None:
            raise ConfigError(
                f"{specs[0].name} is run by {specs[0].run_by}, but platform.toml names no source host"
            )

        return [
            DispatchedTarget(
                _build_target(spec),
                build_ci_runner(
                    spec.run_by,
                    repo=self.source_host.repo,
                    token=self.source_host.token,
                    base_url=getattr(self.source_host, "api", None)
                    if spec.run_by == "github_actions"
                    else getattr(self.source_host, "web", None),
                    username=getattr(self.source_host, "username", None),
                ),
                spec.workflow,
                str(spec.options.get("registry") or ""),
            )
            for spec in specs
        ]

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


def _build_deploy_targets(cfg: dict) -> list[DeployTarget]:
    """The `run_by = "platform"` targets of `[deploy]`, each resolved through the built-in kinds and the `action_platform.deploy_target` entry-point group; the other keys of a target go to its provider."""
    return [_build_target(spec) for spec in parse_targets(cfg) if spec.platform]
