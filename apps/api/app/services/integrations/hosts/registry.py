"""Every code host the platform knows, by kind; built by `host_providers()` and handed to whoever needs it, so tests pass their own."""

from action_platform.core.exception import ProviderError
from app.core.abc import HostProvider
from app.services.integrations.hosts.bitbucket import BitbucketProvider
from app.services.integrations.hosts.github import GithubProvider
from app.services.integrations.hosts.gitlab import GitlabProvider


class HostProviders:
    def __init__(self, *providers: HostProvider) -> None:
        self.by_kind = {p.kind: p for p in providers}

    def __contains__(self, kind: object) -> bool:
        return kind in self.by_kind

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


def host_providers() -> HostProviders:
    return HostProviders(GithubProvider(), GitlabProvider(), BitbucketProvider())
