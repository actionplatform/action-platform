"""Source hosts: where repositories live. One module per provider, chosen by `kind`."""

from __future__ import annotations

from action_platform.abc.source_host import SourceHost
from action_platform.core.exception import ConfigError
from action_platform.providers.source.bitbucket import SourceBitbucket
from action_platform.providers.source.generic import SourceGeneric
from action_platform.providers.source.github import SourceGithub
from action_platform.providers.source.gitlab import SourceGitlab

SOURCE_HOST_KINDS = ("github", "gitlab", "bitbucket", "generic")


def build_source_host(
    kind: str,
    repo: str,
    base_url: str | None = None,
    token: str | None = None,
    username: str | None = None,
) -> SourceHost:
    """A SourceHost for `kind`. Tokens default to the environment (see settings)."""
    if kind == "github":
        return SourceGithub(repo=repo, token=token, base_url=base_url)

    if kind == "gitlab":
        return SourceGitlab(repo=repo, token=token, base_url=base_url)

    if kind == "bitbucket":
        return SourceBitbucket(
            repo=repo, token=token, username=username, base_url=base_url
        )

    if kind in ("generic", "other"):
        return SourceGeneric(
            repo=repo, token=token, username=username, base_url=base_url
        )

    raise ConfigError(
        f"unknown source_host kind: {kind} (available: {', '.join(SOURCE_HOST_KINDS)})"
    )


__all__ = ["SOURCE_HOST_KINDS", "SourceHost", "build_source_host"]
