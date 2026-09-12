"""Action Platform Config."""

from __future__ import annotations

import tomllib
from pathlib import Path

from action_platform.abc.ci_runner import CIRunner
from action_platform.abc.deploy_target import DeployTarget
from action_platform.abc.source_host import SourceHost
from action_platform.core.exception import ConfigError


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

    @property
    def deploy(self) -> list[DeployTarget]:
        """Targets resolve lazily: loading platform.toml never needs a provider installed."""
        if self._deploy is None:
            self._deploy = _build_deploy_targets(self._deploy_spec)

        return self._deploy

    @classmethod
    def from_toml(cls, path: Path) -> "Config":
        if not path.exists():
            raise ConfigError(f"platform.toml not found at {path}")

        data = tomllib.loads(path.read_text())
        project = data.get("project", {})

        config = cls(
            source_host=_build_source_host(data.get("source_host", {})),
            project_name=project.get("name", ""),
            language=project.get("language", ""),
        )
        config._deploy_spec = data.get("deploy", {})

        return config


def _build_source_host(cfg: dict) -> SourceHost | None:
    kind = cfg.get("kind")

    if not kind:
        return None

    if kind == "github":
        from action_platform.providers.source_github import SourceGithub

        return SourceGithub(repo=cfg["repo"])

    raise ConfigError(f"unknown source_host kind: {kind}")


def _build_deploy_targets(cfg: dict) -> list[DeployTarget]:
    """`[deploy] target = "<name>"` resolved through the `action_platform.deploy_target`
    entry-point group; remaining keys of the table are passed to the provider."""
    target = cfg.get("target")

    if not target:
        return []

    from action_platform.core.module import load_deploy_targets

    providers = load_deploy_targets()

    if target not in providers:
        installed = ", ".join(sorted(providers)) or "none"
        raise ConfigError(
            f"no provider installed for deploy target {target!r} (installed: {installed})"
        )

    kwargs = {k: v for k, v in cfg.items() if k != "target"}

    return [providers[target](**kwargs)]
