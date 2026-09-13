"""Source-host credentials handed to the API per request by the web app.

Nothing is stored here: the web app keeps them (encrypted, per
organization) and sends them with the calls that need them — push,
release, pull request. While such a call runs, git authenticates with the
same token through a credential helper injected via the environment.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

from pydantic import BaseModel

from action_platform.core.config import Config
from action_platform.core.flow import git
from action_platform.providers.source import build_source_host

GIT_USERNAMES = {
    "github": "x-access-token",
    "gitlab": "oauth2",
    "bitbucket": "x-token-auth",
}


class SourceCredentials(BaseModel):
    kind: str
    token: str
    username: Optional[str] = None
    base_url: Optional[str] = None
    owner: Optional[str] = None


def apply(config: Config, creds: Optional[SourceCredentials]) -> Config:
    """Rebuild config.source_host with the request's token instead of the environment's."""
    if creds is None or config.source_host is None:
        return config

    config.source_host = build_source_host(
        creds.kind,
        config.source_host.repo,
        base_url=creds.base_url,
        token=creds.token,
        username=creds.username,
    )

    return config


@contextmanager
def git_auth(creds: Optional[SourceCredentials]) -> Iterator[None]:
    """Make every git subprocess in this block authenticate with `creds`.

    The credentials live in a context variable read by `git.git_env()`, so
    they follow this request only — concurrent requests on other threads or
    tasks never see them — and reach git through GIT_CONFIG_{COUNT,KEY,VALUE}
    (git ≥ 2.31) as a credential helper that answers from two variables, so
    the token never lands in .git/config, on a command line, or in the
    process environment.
    """
    if creds is None:
        yield
        return

    username = creds.username or GIT_USERNAMES.get(creds.kind, "git")
    helper = '!f() { printf \'username=%s\\npassword=%s\\n\' "$AP_GIT_USER" "$AP_GIT_TOKEN"; }; f'
    token = git.AUTH_ENV.set(
        {
            "AP_GIT_USER": username,
            "AP_GIT_TOKEN": creds.token,
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": "credential.helper",
            "GIT_CONFIG_VALUE_0": "",
            "GIT_CONFIG_KEY_1": "credential.helper",
            "GIT_CONFIG_VALUE_1": helper,
        }
    )

    try:
        yield
    finally:
        git.AUTH_ENV.reset(token)
