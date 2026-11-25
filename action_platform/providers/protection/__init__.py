"""Branch protection: git-flow enforced by the code host itself. One module per host, chosen by `kind`."""

from __future__ import annotations

from typing import Optional

from action_platform.abc.branch_protection import BranchProtection
from action_platform.core.exception import ProviderError
from action_platform.core.flow.protection import Identity
from action_platform.providers.protection.bitbucket import BitbucketProtection
from action_platform.providers.protection.github import GithubProtection
from action_platform.providers.protection.gitlab import GitlabProtection

PROTECTION_KINDS = ("github", "gitlab", "bitbucket")


def build_branch_protection(
    kind: str,
    repo: str,
    token: str,
    base_url: Optional[str] = None,
    username: Optional[str] = None,
    app: Optional[Identity] = None,
) -> BranchProtection:
    if kind == "github":
        return GithubProtection(repo, token, base_url, app)

    if kind == "gitlab":
        return GitlabProtection(repo, token, base_url)

    if kind == "bitbucket":
        return BitbucketProtection(repo, token, username)

    raise ProviderError(
        f"{kind or 'this host'} has no branch protection the platform can apply"
    )


__all__ = [
    "PROTECTION_KINDS",
    "BitbucketProtection",
    "BranchProtection",
    "GithubProtection",
    "GitlabProtection",
    "build_branch_protection",
]
