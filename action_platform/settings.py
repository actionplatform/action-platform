"""Action Platform settings module: the configuration slices of `action_platform.options`, read from the process environment."""

from __future__ import annotations

import os
from typing import Any, Callable, Optional

from action_platform.core import files
from action_platform.options import (
    ApiConfig,
    DatabaseConfig,
    Env,
    GitConfig,
    ObservabilityConfig,
    SourceTokens,
    TemplatesConfig,
    WorkspacesConfig,
    database_url_from_parts,
    secret,
)

SLICES: dict[str, Callable[[Env], Any]] = {
    "templates": TemplatesConfig.from_env,
    "workspaces": WorkspacesConfig.from_env,
    "git": GitConfig.from_env,
    "tokens": SourceTokens.from_env,
    "api": ApiConfig.from_env,
    "database": DatabaseConfig.from_env,
    "observability": ObservabilityConfig.from_env,
}


class Settings:
    """
    Import:
        from action_platform.settings import Settings, settings

    Example:
        Settings.from_env({"AP_DATABASE_URL": "sqlite://"}).database.url

    One attribute per slice — `templates`, `workspaces`, `git`, `tokens`,
    `api`, `database`, `observability` — each read from its source when asked
    for, never at import: `settings` follows the process environment as it is
    now (after an entry point loaded `.env`), and `Settings.from_env(mapping)`
    answers from a mapping of its own.
    """

    CONFIG_FILE = files.CONFIG_FILE
    LAST_VERSION_FILE = files.LAST_VERSION_FILE
    HOOKS_DIR = files.HOOKS_DIR
    CHANGELOG_FILE = files.CHANGELOG_FILE

    templates: TemplatesConfig
    workspaces: WorkspacesConfig
    git: GitConfig
    tokens: SourceTokens
    api: ApiConfig
    database: DatabaseConfig
    observability: ObservabilityConfig

    def __init__(self, env: Optional[Env] = None) -> None:
        self._env = env

    @classmethod
    def from_env(cls, env: Optional[Env] = None) -> "Settings":
        return cls(env)

    @property
    def source(self) -> Env:
        return os.environ if self._env is None else self._env

    def env(self, name: str) -> str:
        return self.source.get(name, "")

    def __getattr__(self, name: str) -> Any:
        read = SLICES.get(name)

        if read is None:
            raise AttributeError(name)

        return read(self.source)


settings = Settings()

__all__ = ["SLICES", "Settings", "database_url_from_parts", "secret", "settings"]
