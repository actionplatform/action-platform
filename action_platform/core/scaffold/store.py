"""Local checkouts of template repositories: the official one and any the user adds."""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

from action_platform.abc.template_store import TemplateStoreABC
from action_platform.core.exception import TemplateError
from action_platform.core.flow.git import (
    BadRef,
    UnsafeUrl,
    check_ref,
    check_remote_url,
    git_env,
)
from action_platform.logging import logger
from action_platform.settings import settings


@dataclass(frozen=True)
class TemplateSource:
    """A git repository laid out like actionplatform/templates: index.json plus projects/, cloud/, service/."""

    url: str
    ref: str = "main"
    name: str = ""

    @classmethod
    def parse(cls, spec: str, name: str = "") -> "TemplateSource":
        """`url[@ref]`; a local path is accepted as well."""
        url, _, ref = spec.rpartition("@")

        if not url or "/" in ref or ref.startswith("git"):
            url, ref = spec, "main"

        return cls(url=url, ref=ref or "main", name=name)

    @property
    def label(self) -> str:
        return self.name or self.url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")

    @property
    def cache(self) -> Path:
        key = hashlib.sha256(f"{self.url}@{self.ref}".encode()).hexdigest()[:16]

        return settings.TEMPLATES_CACHE.parent / "sources" / key


class TemplateStore(TemplateStoreABC):
    """Clones template repositories under the cache directory and keeps them fresh; a refresh that fails falls back to the copy on disk unless `update` insists."""

    def checkout(self, source: TemplateSource, update: bool = False) -> Path:
        cache = source.cache

        try:
            check_remote_url(source.url)
            check_ref(source.ref)
        except (UnsafeUrl, BadRef) as e:
            raise TemplateError(str(e)) from e

        if not cache.exists():
            logger.info("cloning %s@%s", source.url, source.ref)
            cache.parent.mkdir(parents=True, exist_ok=True)
            self._git(
                "clone",
                "--depth",
                "1",
                "--branch",
                source.ref,
                "--end-of-options",
                source.url,
                str(cache),
            )

            return cache

        try:
            self._git(
                "-C",
                str(cache),
                "fetch",
                "--depth",
                "1",
                "--quiet",
                "--end-of-options",
                "origin",
                source.ref,
            )
            self._git("-C", str(cache), "checkout", "--quiet", "--force", "FETCH_HEAD")
        except TemplateError as e:
            if update:
                raise

            logger.warning(
                "source %s not refreshed (%s); using local copy", source.label, e
            )

        return cache

    def official(self, update: bool = False) -> Path:
        """The official templates repository: ACTION_PLATFORM_TEMPLATES when set, else a cached clone of ACTION_PLATFORM_TEMPLATES_REPO."""
        local = settings.TEMPLATES_DIR

        if local is not None:
            path = Path(local).expanduser()

            if not path.exists():
                raise TemplateError(
                    f"ACTION_PLATFORM_TEMPLATES points to missing path: {path}"
                )

            return path

        cache = settings.TEMPLATES_CACHE

        if not cache.exists():
            logger.info("cloning %s", settings.TEMPLATES_REPO)
            cache.parent.mkdir(parents=True, exist_ok=True)
            self._git(
                "clone",
                "--depth",
                "1",
                "--branch",
                settings.TEMPLATES_REF,
                settings.TEMPLATES_REPO,
                str(cache),
            )

            return cache

        try:
            self._git("-C", str(cache), "pull", "--ff-only", "--quiet")
        except TemplateError as e:
            if update:
                raise

            logger.warning("templates cache not refreshed (%s); using local copy", e)

        return cache

    @staticmethod
    def _git(*args: str) -> None:
        result = subprocess.run(
            ["git", *args], capture_output=True, text=True, env=git_env()
        )

        if result.returncode != 0:
            raise TemplateError(result.stderr.strip() or "git failed")
