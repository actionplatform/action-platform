"""Source hosts: where repositories live. One module per provider, chosen by `kind`."""

from __future__ import annotations

from action_platform.abc.source_host import SourceHost
from action_platform.core.exception import ConfigError

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
        from action_platform.providers.source.github import SourceGithub

        return SourceGithub(repo=repo, token=token, base_url=base_url)

    if kind == "gitlab":
        from action_platform.providers.source.gitlab import SourceGitlab

        return SourceGitlab(repo=repo, token=token, base_url=base_url)

    if kind == "bitbucket":
        from action_platform.providers.source.bitbucket import SourceBitbucket

        return SourceBitbucket(
            repo=repo, token=token, username=username, base_url=base_url
        )

    if kind in ("generic", "other"):
        from action_platform.providers.source.generic import SourceGeneric

        return SourceGeneric(
            repo=repo, token=token, username=username, base_url=base_url
        )

    raise ConfigError(
        f"unknown source_host kind: {kind} (available: {', '.join(SOURCE_HOST_KINDS)})"
    )


__all__ = ["SOURCE_HOST_KINDS", "SourceHost", "build_source_host"]
