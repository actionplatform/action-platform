"""Access on the organization's services: the request bodies; the answers are the library's models."""

from typing import Optional

from pydantic import BaseModel, Field

from action_platform.core.service_access.models import Audit, Plan, Who
from action_platform.providers.access.github import BranchProtection, OrgSettings

__all__ = [
    "Audit",
    "BranchProtection",
    "GrantRequest",
    "OrgSettings",
    "OffboardRequest",
    "PersonGrant",
    "Plan",
    "RevokeRequest",
    "SyncRequest",
    "Who",
]


class SyncRequest(BaseModel):
    service: Optional[str] = None
    apply: bool = False
    reimport: bool = False
    links: Optional[dict[str, dict[str, str]]] = Field(
        None,
        description="{member email: {service: account}} for accounts that are not the member's email",
    )


class GrantRequest(BaseModel):
    person: str
    service: str
    resource: str
    level: str
    account: Optional[str] = None
    apply: bool = False


class PersonGrant(BaseModel):
    service: str
    resource: str
    level: str
    account: Optional[str] = None
    apply: bool = False


class RevokeRequest(BaseModel):
    person: str
    service: str
    resource: str
    apply: bool = False


class OffboardRequest(BaseModel):
    person: str
    apply: bool = False
    remove_from_platform: bool = False
