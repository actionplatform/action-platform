"""Read-only checks of the repositories of the GitHub organization the platform's GitHub connection manages: branch protection and repository settings."""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import Field

from action_platform.mcp.annotations import READ_ONLY, tool
from action_platform.mcp.tools.remote.common import OrgId
from action_platform.providers.access.github.models import BranchProtection, OrgSettings
from action_platform.remote.client import Remote

Repo = Annotated[
    Optional[str], Field(description="Only this repository; every repository if empty")
]


def register(mcp: Any, remote: Remote) -> None:
    @tool(mcp, annotations=READ_ONLY)
    def github_branch_protection(
        repo: Repo = None, organization: OrgId = None
    ) -> BranchProtection:
        """Protection of each repository's default branch, from branch protection rules and rulesets: whether it is protected, required approving reviews, required status checks, whether force pushes are allowed. Needs org.manage."""
        return remote.github_branch_protection(repo, organization=organization)

    @tool(mcp, annotations=READ_ONLY)
    def github_repo_settings(
        repo: Repo = None, organization: OrgId = None
    ) -> OrgSettings:
        """Settings of each repository: visibility, default branch, archived, delete branch on merge, auto-merge, secret scanning, push protection, Dependabot alerts and security updates. A value is null when the connection cannot see it. Needs org.manage."""
        return remote.github_repo_settings(repo, organization=organization)
