"""Source hosts: where repositories live. One module per provider, chosen by `kind`."""

from __future__ import annotations

from action_platform.abc.source_host import SourceHost
from action_platform.providers.registry import ProviderRegistry
from action_platform.providers.source.bitbucket import SourceBitbucket
from action_platform.providers.source.generic import SourceGeneric
from action_platform.providers.source.github import SourceGithub
from action_platform.providers.source.gitlab import SourceGitlab

SOURCE_HOSTS: ProviderRegistry[SourceHost] = ProviderRegistry("source_host")
SOURCE_HOSTS.register(SourceGithub)
SOURCE_HOSTS.register(SourceGitlab)
SOURCE_HOSTS.register(SourceBitbucket)
SOURCE_HOSTS.register(SourceGeneric, "other")

SOURCE_HOST_KINDS = SOURCE_HOSTS.kinds()


def build_source_host(
    kind: str,
    repo: str,
    base_url: str | None = None,
    token: str | None = None,
    username: str | None = None,
) -> SourceHost:
    """A SourceHost for `kind`. Tokens default to the environment (see settings)."""
    return SOURCE_HOSTS.build(
        kind, repo=repo, token=token, username=username, base_url=base_url
    )


__all__ = ["SOURCE_HOSTS", "SOURCE_HOST_KINDS", "SourceHost", "build_source_host"]
