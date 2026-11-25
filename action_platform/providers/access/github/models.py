"""What the read tools answer."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RepoProtection(BaseModel):
    repo: str
    default_branch: str
    archived: bool
    protected: Optional[bool] = Field(
        None,
        description="A branch protection rule or an active ruleset applies to the default branch; null when GitHub would not say",
    )
    rule_types: list[str] = Field(
        default_factory=list,
        description="Rule types of the rulesets that apply to the default branch",
    )
    required_reviews: Optional[int] = Field(
        None, description="Approving reviews a pull request needs; 0 when none"
    )
    required_status_checks: list[str] = Field(default_factory=list)
    force_pushes_allowed: Optional[bool] = None
    note: str = Field("", description="Why the protection could not be read")


class BranchProtection(BaseModel):
    org: str
    repos: list[RepoProtection]


class RepoSettings(BaseModel):
    repo: str
    visibility: str
    default_branch: str
    archived: bool
    delete_branch_on_merge: Optional[bool] = None
    allow_auto_merge: Optional[bool] = None
    secret_scanning: Optional[str] = Field(
        None, description="enabled or disabled; null when the token cannot see it"
    )
    secret_scanning_push_protection: Optional[str] = None
    dependabot_alerts: Optional[bool] = Field(
        None, description="null when the token cannot see it"
    )
    dependabot_security_updates: Optional[str] = None


class OrgSettings(BaseModel):
    org: str
    repos: list[RepoSettings]
