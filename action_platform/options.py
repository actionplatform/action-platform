"""Configuration slices: one frozen dataclass per concern, each parsed from an environment mapping by `from_env`.

A module that needs configuration takes the slice it uses — `GitConfig`,
`TemplatesConfig`, `SourceTokens`, `ObservabilityConfig` — never all of it.
`action_platform.settings` assembles them from the process environment.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional
from urllib.parse import quote

Env = Mapping[str, str]

CACHE = Path.home() / ".cache" / "action-platform"


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


@dataclass(frozen=True)
class TemplatesConfig:
    """Where the official templates and the plugins index come from."""

    repo: str = "https://github.com/actionplatform/templates.git"
    ref: str = "main"
    dir: Optional[str] = None
    index_url: str = (
        "https://raw.githubusercontent.com/actionplatform/templates/main/index.json"
    )
    index_ttl: int = 60
    plugins_index_url: str = (
        "https://raw.githubusercontent.com/actionplatform/plugins-index/main/index.json"
    )
    cache: Path = CACHE / "templates"

    @classmethod
    def from_env(cls, env: Env) -> "TemplatesConfig":
        ref = env.get("ACTION_PLATFORM_TEMPLATES_REF", cls.ref)

        return cls(
            repo=env.get("ACTION_PLATFORM_TEMPLATES_REPO", cls.repo),
            ref=ref,
            dir=env.get("ACTION_PLATFORM_TEMPLATES"),
            index_url=env.get(
                "ACTION_PLATFORM_TEMPLATES_INDEX",
                f"https://raw.githubusercontent.com/actionplatform/templates/{ref}/index.json",
            ),
            index_ttl=int(env.get("ACTION_PLATFORM_TEMPLATES_INDEX_TTL", "60")),
            plugins_index_url=env.get(
                "ACTION_PLATFORM_PLUGINS_INDEX", cls.plugins_index_url
            ),
        )


@dataclass(frozen=True)
class WorkspacesConfig:
    """Where the hosted platform keeps its clones, and for how many minutes a fetch stays fresh."""

    root: Path = Path(tempfile.gettempdir()) / "action-platform" / "workspaces"
    ttl: int = 15

    @classmethod
    def from_env(cls, env: Env) -> "WorkspacesConfig":
        return cls(
            root=Path(env.get("AP_WORKSPACES") or cls.root),
            ttl=int(env.get("AP_WORKSPACE_TTL", "15")),
        )


@dataclass(frozen=True)
class GitConfig:
    """Which remotes may be cloned on a user's behalf, and the identity a commit falls back to."""

    allow_file_urls: bool = False
    allow_insecure_http: bool = False
    hosts: tuple[str, ...] = ()
    author_name: str = "Action Platform"
    author_email: str = "cloud@actionplatform.io"

    @classmethod
    def from_env(cls, env: Env) -> "GitConfig":
        return cls(
            allow_file_urls=env.get("AP_ALLOW_FILE_URLS") == "1",
            allow_insecure_http=env.get("AP_ALLOW_INSECURE_HTTP") == "1",
            hosts=tuple(
                h.strip().lower()
                for h in env.get("ACTION_PLATFORM_GIT_HOSTS", "").split(",")
                if h.strip()
            ),
            author_name=env.get("AP_GIT_AUTHOR_NAME", cls.author_name),
            author_email=env.get("AP_GIT_AUTHOR_EMAIL", cls.author_email),
        )


@dataclass(frozen=True)
class SourceTokens:
    """Code-host credentials of the machine the CLI runs on."""

    github: Optional[str] = None
    gitlab: Optional[str] = None
    bitbucket: Optional[str] = None
    bitbucket_username: Optional[str] = None

    @classmethod
    def from_env(cls, env: Env) -> "SourceTokens":
        return cls(
            github=env.get("ACTION_PLATFORM_GITHUB_TOKEN") or env.get("GH_TOKEN"),
            gitlab=env.get("ACTION_PLATFORM_GITLAB_TOKEN") or env.get("GITLAB_TOKEN"),
            bitbucket=env.get("ACTION_PLATFORM_BITBUCKET_TOKEN"),
            bitbucket_username=env.get("ACTION_PLATFORM_BITBUCKET_USERNAME"),
        )


@dataclass(frozen=True)
class ApiConfig:
    """How the hosted API authenticates its callers and names itself."""

    token: str = ""
    allow_unauthenticated: bool = False
    auth_secret: str = ""
    public_url: str = ""
    forwarded_allow_ips: str = "*"
    trusted_proxies: str = (
        "127.0.0.0/8,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,::1/128,fc00::/7"
    )

    @classmethod
    def from_env(cls, env: Env) -> "ApiConfig":
        return cls(
            token=secret("AP_API_TOKEN", env=env),
            allow_unauthenticated=env.get("AP_ALLOW_UNAUTHENTICATED", "") == "1",
            auth_secret=secret("AP_AUTH_SECRET", "BETTER_AUTH_SECRET", env=env),
            public_url=env.get("AP_PUBLIC_URL") or env.get("PUBLIC_URL", ""),
            forwarded_allow_ips=env.get("AP_FORWARDED_ALLOW_IPS", "*"),
            trusted_proxies=env.get("AP_TRUSTED_PROXIES", cls.trusted_proxies),
        )


@dataclass(frozen=True)
class DatabaseConfig:
    """The database the hosted API owns."""

    url: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    auto_migrate: bool = True

    @classmethod
    def from_env(cls, env: Env) -> "DatabaseConfig":
        return cls(
            url=secret("AP_DATABASE_URL", "DATABASE_URL", env=env)
            or database_url_from_parts(env),
            pool_size=int(env.get("AP_DATABASE_POOL_SIZE", "10")),
            max_overflow=int(env.get("AP_DATABASE_MAX_OVERFLOW", "20")),
            auto_migrate=env.get("AP_DATABASE_AUTO_MIGRATE", "1")
            not in ("0", "false", "no"),
        )


@dataclass(frozen=True)
class ObservabilityConfig:
    """Sentry reporting; an empty `dsn` keeps it off."""

    dsn: str = ""
    environment: str = "production"
    traces_sample_rate: float = 0.1

    @classmethod
    def from_env(cls, env: Env) -> "ObservabilityConfig":
        return cls(
            dsn=env.get("AP_SENTRY_DSN", ""),
            environment=env.get("AP_SENTRY_ENVIRONMENT", "production"),
            traces_sample_rate=float(env.get("AP_SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        )
