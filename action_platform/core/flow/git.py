"""What every git call shares: safe ref and URL checks, the per-request credentials, the protocol policy. Commands themselves live on `Repository`."""

from __future__ import annotations

import os
import re
from contextvars import ContextVar
from urllib.parse import urlsplit

from action_platform.settings import settings


AUTH_ENV: ContextVar[dict[str, str] | None] = ContextVar("git_auth_env", default=None)


class UnsafeUrl(ValueError):
    pass


class BadRef(ValueError):
    pass


REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


def check_ref(name: str) -> str:
    """A branch or tag name that is safe to hand to git as an argument: no leading dash, no path tricks."""
    if (
        not name
        or not REF_RE.match(name)
        or ".." in name
        or "@{" in name
        or name.endswith(".lock")
        or name.endswith("/")
        or "//" in name
    ):
        raise BadRef(f"invalid git ref: {name!r}")

    return name


def check_remote_url(url: str) -> str:
    """Only https (and http / file when the operator opted in) may be cloned or fetched on behalf of a user; ACTION_PLATFORM_GIT_HOSTS narrows the hosts further."""
    parts = urlsplit(url)
    allowed = (
        parts.scheme == "https"
        or (parts.scheme == "http" and settings.ALLOW_INSECURE_HTTP)
        or (parts.scheme == "file" and settings.ALLOW_FILE_URLS)
    )

    if not allowed:
        raise UnsafeUrl(f"unsupported git url: {url} (https:// only)")

    host = (parts.hostname or "").lower()

    if (
        parts.scheme != "file"
        and settings.GIT_HOSTS
        and not any(host == h or host.endswith("." + h) for h in settings.GIT_HOSTS)
    ):
        raise UnsafeUrl(
            f"git host {host} is not allowed (ACTION_PLATFORM_GIT_HOSTS: {', '.join(settings.GIT_HOSTS)})"
        )

    return url


def git_env() -> dict[str, str]:
    """Environment for a git subprocess: the process environment, the credentials of the current request, and a protocol policy: https always, http only when opted in, ssh/git never, local paths only for direct commands (never from submodules)."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    env.setdefault("GIT_AUTHOR_NAME", settings.GIT_AUTHOR_NAME)
    env.setdefault("GIT_AUTHOR_EMAIL", settings.GIT_AUTHOR_EMAIL)
    env.setdefault("GIT_COMMITTER_NAME", settings.GIT_AUTHOR_NAME)
    env.setdefault("GIT_COMMITTER_EMAIL", settings.GIT_AUTHOR_EMAIL)
    extra = {**(AUTH_ENV.get() or {})}
    count = int(extra.get("GIT_CONFIG_COUNT", "0"))
    policy = {
        "protocol.allow": "never",
        "protocol.https.allow": "always",
        "protocol.http.allow": "always" if settings.ALLOW_INSECURE_HTTP else "never",
        "protocol.file.allow": "always" if settings.ALLOW_FILE_URLS else "user",
    }

    for key, value in policy.items():
        extra[f"GIT_CONFIG_KEY_{count}"] = key
        extra[f"GIT_CONFIG_VALUE_{count}"] = value
        count += 1

    extra["GIT_CONFIG_COUNT"] = str(count)
    env.update(extra)

    return env
