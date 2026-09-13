"""Vcs ABC: what the release, git-flow and scaffolding code need from a working copy."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class Vcs(ABC):
    path: Path

    @property
    @abstractmethod
    def branch(self) -> str: ...

    @abstractmethod
    def is_clean(self) -> bool: ...

    @abstractmethod
    def changed_files(self) -> list[str]: ...

    @abstractmethod
    def remote_url(self, remote: str = "origin") -> str: ...

    @abstractmethod
    def tags(self) -> list[str]: ...

    @abstractmethod
    def latest_tag(self, match: str | None = None) -> str | None: ...

    @abstractmethod
    def commits_since(
        self, ref: str | None, paths: list[str] | None = None
    ) -> list[str]: ...

    @abstractmethod
    def fetch(
        self, remote: str = "origin", prune: bool = True, tags: bool = True
    ) -> None: ...

    @abstractmethod
    def checkout(
        self, branch: str, create: bool = False, start: str | None = None
    ) -> None: ...

    @abstractmethod
    def add(self, paths: list[str]) -> None: ...

    @abstractmethod
    def add_all(self) -> None: ...

    @abstractmethod
    def commit(self, message: str) -> None: ...

    @abstractmethod
    def tag(self, name: str, message: str | None = None) -> None: ...

    @abstractmethod
    def push(self, refspec: str = "HEAD", remote: str = "origin") -> None: ...

    @abstractmethod
    def push_tag(self, tag: str, remote: str = "origin") -> None: ...

    @abstractmethod
    def push_upstream(self, branch: str, remote: str = "origin") -> None: ...
