"""Action Platform settings module."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, Optional
from urllib.parse import quote

Env = Mapping[str, str]


def secret(*names: str, env: Optional[Env] = None) -> str:
    """The first of `names` set in `env` (default: the process environment) — `<NAME>_FILE` first, a path whose content is the value (Docker and Kubernetes secrets), then `<NAME>` itself."""
    env = os.environ if env is None else env

    for name in names:
        path = env.get(f"{name}_FILE")

        if path:
            try:
                return Path(path).read_text().strip()
            except OSError:
                pass

        value = env.get(name)

        if value:
            return value

    return ""


def database_url_from_parts(env: Optional[Env] = None) -> str:
    """`AP_DB_HOST`, `AP_DB_PORT`, `AP_DB_NAME`, `AP_DB_USER` and `AP_DB_PASSWORD` (or `_FILE`) assembled into a URL, for a deployment that keeps the password out of the environment."""
    env = os.environ if env is None else env
    host = env.get("AP_DB_HOST")

    if not host:
        return ""

    user = env.get("AP_DB_USER", "action_platform")
    name = env.get("AP_DB_NAME", "action_platform")
    port = env.get("AP_DB_PORT", "5432")
    password = secret("AP_DB_PASSWORD", env=env)

    return f"postgres://{user}:{quote(password, safe='')}@{host}:{port}/{name}"


def _templates_ref(env: Env) -> str:
    return env.get("ACTION_PLATFORM_TEMPLATES_REF", "main")


FIELDS: dict[str, Callable[[Env], Any]] = {
    "TEMPLATES_REPO": lambda env: env.get(
        "ACTION_PLATFORM_TEMPLATES_REPO",
        "https://github.com/actionplatform/templates.git",
    ),
    "TEMPLATES_REF": _templates_ref,
    "TEMPLATES_DIR": lambda env: env.get("ACTION_PLATFORM_TEMPLATES"),
    "TEMPLATES_INDEX_URL": lambda env: env.get(
        "ACTION_PLATFORM_TEMPLATES_INDEX",
        f"https://raw.githubusercontent.com/actionplatform/templates/{_templates_ref(env)}/index.json",
    ),
    "TEMPLATES_INDEX_TTL": lambda env: int(
        env.get("ACTION_PLATFORM_TEMPLATES_INDEX_TTL", "60")
    ),
    "PLUGINS_INDEX_URL": lambda env: env.get(
        "ACTION_PLATFORM_PLUGINS_INDEX",
        "https://raw.githubusercontent.com/actionplatform/plugins-index/main/index.json",
    ),
    "TEMPLATES_CACHE": lambda env: (
        Path.home() / ".cache" / "action-platform" / "templates"
    ),
    "WORKSPACES": lambda env: Path(
        env.get("AP_WORKSPACES")
        or Path(tempfile.gettempdir()) / "action-platform" / "workspaces"
    ),
    "WORKSPACE_TTL": lambda env: int(env.get("AP_WORKSPACE_TTL", "15")),
    "ALLOW_FILE_URLS": lambda env: env.get("AP_ALLOW_FILE_URLS") == "1",
    "ALLOW_INSECURE_HTTP": lambda env: env.get("AP_ALLOW_INSECURE_HTTP") == "1",
    "GIT_HOSTS": lambda env: [
        h.strip().lower()
        for h in env.get("ACTION_PLATFORM_GIT_HOSTS", "").split(",")
        if h.strip()
    ],
    "GITHUB_TOKEN": lambda env: (
        env.get("ACTION_PLATFORM_GITHUB_TOKEN") or env.get("GH_TOKEN")
    ),
    "API_TOKEN": lambda env: secret("AP_API_TOKEN", env=env),
    "ALLOW_UNAUTHENTICATED_API": lambda env: (
        env.get("AP_ALLOW_UNAUTHENTICATED", "") == "1"
    ),
    "FORWARDED_ALLOW_IPS": lambda env: env.get("AP_FORWARDED_ALLOW_IPS", "*"),
    "DATABASE_URL": lambda env: (
        secret("AP_DATABASE_URL", "DATABASE_URL", env=env)
        or database_url_from_parts(env)
    ),
    "DATABASE_POOL_SIZE": lambda env: int(env.get("AP_DATABASE_POOL_SIZE", "10")),
    "DATABASE_AUTO_MIGRATE": lambda env: (
        env.get("AP_DATABASE_AUTO_MIGRATE", "1") not in ("0", "false", "no")
    ),
    "DATABASE_MAX_OVERFLOW": lambda env: int(env.get("AP_DATABASE_MAX_OVERFLOW", "20")),
    "AUTH_SECRET": lambda env: secret("AP_AUTH_SECRET", "BETTER_AUTH_SECRET", env=env),
    "PUBLIC_URL": lambda env: env.get("AP_PUBLIC_URL") or env.get("PUBLIC_URL", ""),
    "TRUSTED_PROXIES": lambda env: env.get(
        "AP_TRUSTED_PROXIES",
        "127.0.0.0/8,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,::1/128,fc00::/7",
    ),
    "SENTRY_DSN": lambda env: env.get("AP_SENTRY_DSN", ""),
    "SENTRY_ENVIRONMENT": lambda env: env.get("AP_SENTRY_ENVIRONMENT", "production"),
    "SENTRY_TRACES_SAMPLE_RATE": lambda env: float(
        env.get("AP_SENTRY_TRACES_SAMPLE_RATE", "0.1")
    ),
    "GIT_AUTHOR_NAME": lambda env: env.get("AP_GIT_AUTHOR_NAME", "Action Platform"),
    "GIT_AUTHOR_EMAIL": lambda env: env.get(
        "AP_GIT_AUTHOR_EMAIL", "cloud@actionplatform.io"
    ),
    "GITLAB_TOKEN": lambda env: (
        env.get("ACTION_PLATFORM_GITLAB_TOKEN") or env.get("GITLAB_TOKEN")
    ),
    "BITBUCKET_TOKEN": lambda env: env.get("ACTION_PLATFORM_BITBUCKET_TOKEN"),
    "BITBUCKET_USERNAME": lambda env: env.get("ACTION_PLATFORM_BITBUCKET_USERNAME"),
}


class Settings:
    """
    Import:
        from action_platform.settings import Settings, settings

    Example:
        Settings.from_env({"AP_DATABASE_URL": "sqlite://"}).DATABASE_URL

    Every setting is read from its source when asked for, never at import:
    `settings` follows the process environment as it is now (after an entry
    point loaded `.env`), and `Settings.from_env(mapping)` answers from a
    mapping of its own — a test builds one instead of patching the shared one.
    """

    CONFIG_FILE = "platform.toml"
    LAST_VERSION_FILE = "LAST_VERSION"
    HOOKS_DIR = Path(".action-platform/hooks")
    CHANGELOG_FILE = "CHANGELOG.md"

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
        read = FIELDS.get(name)

        if read is None:
            raise AttributeError(name)

        return read(self.source)


settings = Settings()
