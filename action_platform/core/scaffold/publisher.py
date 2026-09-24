"""How a generated project reaches its source host: git init, hooks, first commit, remote repository, push."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Protocol

from action_platform.abc.source_host import SupportsRepoCreation
from action_platform.core.config import Config
from action_platform.core.exception import TemplateError
from action_platform.core.flow.repository import Repository
from action_platform.core.manifest import Manifest
from action_platform.core.wiring import wired
from action_platform.providers.source import build_source_host
from action_platform.core.files import CONFIG_FILE


class SourceCredentialsLike(Protocol):
    kind: str
    token: str
    username: str | None
    base_url: str | None


class Publisher:
    """Turns a project directory into a pushed repository on the host its [source_host] names.

    No secrets are written: the deploy workflow needs them, but which ones and
    from where is the operator's call — DEPLOY.md in the project lists them.
    `credentials` (kind, token, username, base_url) override the environment's.
    """

    def __init__(
        self, project: Path, credentials: SourceCredentialsLike | None = None
    ) -> None:
        self.project = Path(project)
        self.credentials = credentials

    def push(self, private: bool = False, branch: str = "main") -> str:
        config = self._config()
        repo = self.initialize(branch)

        if not isinstance(config.source_host, SupportsRepoCreation):
            raise TemplateError(
                f"{config.source_host.name} cannot create repositories; create it by hand and push"
            )

        url = config.source_host.create_repository(
            config.source_host.repo,
            description=Manifest.of(self.project).project.get("description", ""),
            private=private,
        )

        if not repo.remote_url():
            repo.add_remote(url)

        try:
            repo.push_upstream(branch)
        except subprocess.CalledProcessError as e:
            raise TemplateError(
                f"push failed: {e.stderr.strip() if e.stderr else e}"
            ) from e

        return url

    def initialize(self, branch: str = "main") -> Repository:
        """The project as a git repository with the platform's hooks and everything committed."""
        repo = (
            Repository(self.project)
            if (self.project / ".git").exists()
            else Repository.init(self.project, branch=branch)
        )

        wired.gitflow(repo).install_hooks()
        repo.add_all()

        if not repo.is_clean():
            repo.commit("chore: bootstrap project from action-platform")

        return repo

    def _config(self) -> Config:
        config = Config.from_toml(self.project / CONFIG_FILE)
        credentials = self.credentials

        if (
            credentials is not None
            and credentials.token
            and config.source_host is not None
        ):
            config.source_host = build_source_host(
                credentials.kind,
                config.source_host.repo,
                base_url=credentials.base_url,
                token=credentials.token,
                username=credentials.username,
            )

        if config.source_host is None:
            raise TemplateError("platform.toml has no [source_host]; cannot push")

        return config


def push_project(
    project: Path,
    private: bool = False,
    branch: str = "main",
    credentials: SourceCredentialsLike | None = None,
) -> str:
    """git init, first commit, create the remote via [source_host], push."""
    return Publisher(project, credentials).push(private, branch)
