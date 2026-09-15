"""HostDirectory ABC."""

from abc import ABC, abstractmethod
from typing import Any


class HostDirectory(ABC):
    """What a code-host token can see for an import: organizations, repositories, teams, people and projects."""

    kind: str

    @abstractmethod
    def organizations(self) -> list[dict[str, Any]]:
        """The account itself first, then every organization the token can see: login, name, kind (user|org), avatar."""

    @abstractmethod
    def repositories(self, login: str) -> list[dict[str, Any]]:
        """Repositories of `login`: full_name, name, description, private, archived, fork, language, default_branch, url, pushed_at."""

    @abstractmethod
    def teams(self, login: str) -> list[dict[str, Any]]:
        """Teams of `login`: slug, name, description, members (logins), repositories (full names)."""

    @abstractmethod
    def people(self, login: str) -> list[dict[str, Any]]:
        """Members of `login`: login, name, email (public one or None), avatar."""

    @abstractmethod
    def projects(self, login: str) -> list[dict[str, Any]]:
        """Projects of `login`: number, title, description, closed, url, repositories (full names)."""
