"""Every code host the platform knows, by kind."""

from action_platform_api.core.abc import HostProvider
from action_platform_api.services.hosts.bitbucket import BitbucketProvider
from action_platform_api.services.hosts.github import GithubProvider
from action_platform_api.services.hosts.gitlab import GitlabProvider
from action_platform.core.exception import ProviderError


class HostProviders:
    def __init__(self, *providers: HostProvider) -> None:
        self.by_kind = {p.kind: p for p in providers}

    def get(self, kind: str) -> HostProvider:
        provider = self.by_kind.get(kind)

        if provider is None:
            raise ProviderError(f"unknown code host: {kind}")

        return provider

    def info(self) -> dict[str, dict[str, str]]:
        return {
            p.kind: {
                "label": p.label,
                "scopes": p.scopes,
                "callback_hint": p.callback_hint,
            }
            for p in self.by_kind.values()
        }

    @property
    def github(self) -> GithubProvider:
        return self.by_kind["github"]

    @property
    def bitbucket(self) -> BitbucketProvider:
        return self.by_kind["bitbucket"]


PROVIDERS = HostProviders(GithubProvider(), GitlabProvider(), BitbucketProvider())
