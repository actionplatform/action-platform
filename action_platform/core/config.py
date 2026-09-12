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
        from action_platform.providers import SourceGithub, CIJenkins, DeployDokploy

    Example:
        config = Config(
            source_host=SourceGithub(repo="FernandoCelmer/my-project"),
            ci=[CIJenkins(url="...", job="my-project-build")],
            deploy=[DeployDokploy(url="...", app="my-project-prod")],
        )

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
        self.deploy = deploy or []
        self.project_name = project_name
        self.language = language

    @classmethod
    def from_toml(cls, path: Path) -> "Config":
        if not path.exists():
            raise ConfigError(f"platform.toml not found at {path}")
        data = tomllib.loads(path.read_text())
        project = data.get("project", {})
        return cls(
            source_host=_build_source_host(data.get("source_host", {})),
            project_name=project.get("name", ""),
            language=project.get("language", ""),
        )


def _build_source_host(cfg: dict) -> SourceHost | None:
    kind = cfg.get("kind")
    if not kind:
        return None
    if kind == "github":
        from action_platform.providers.source_github import SourceGithub

        return SourceGithub(repo=cfg["repo"])
    raise ConfigError(f"unknown source_host kind: {kind}")
