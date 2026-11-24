"""What the tools and commands answer — the output schemas the MCP client sees."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Status = Literal["planned", "applied", "refused", "failed"]


class GrantRow(BaseModel):
    service: str
    account: str
    resource: str
    level: str
    person: Optional[str] = Field(
        None, description="The member's email when the account is linked to one"
    )
    source: Optional[str] = Field(
        None,
        description="Why the mapping wants it: role:<role>, team:<slug>, person, kept",
    )


class Change(BaseModel):
    action: Literal["add", "change", "remove"]
    service: str
    account: str
    resource: str
    level: str
    previous: Optional[str] = None
    status: Status = "planned"
    detail: Optional[str] = None


class ServiceAudit(BaseModel):
    service: str
    ok: bool
    imported: bool = Field(
        True, description="False until a sync imports this service; no drift until then"
    )
    error: Optional[str] = None
    levels: dict[str, list[str]] = Field(
        default_factory=dict,
        description="The resource kinds this service grants and their levels, lowest first",
    )
    live: int = Field(0, description="Grants the service holds")
    wanted: int = Field(0, description="Grants the mapping asks for")
    drift: list[Change] = Field(
        default_factory=list, description="What a sync would change"
    )
    members_without_account: list[str] = Field(default_factory=list)
    outside_accounts: list[str] = Field(
        default_factory=list,
        description="Accounts with access that belong to no member; a sync keeps the ones imported into `keep` and removes the rest",
    )


class Audit(BaseModel):
    organization_members: int
    imported: list[str] = Field(
        default_factory=list, description="Services whose live state is in the mapping"
    )
    services: list[ServiceAudit]


class PersonOut(BaseModel):
    email: str
    name: str
    role: Optional[str] = None
    teams: list[str] = Field(default_factory=list)
    accounts: dict[str, str] = Field(default_factory=dict)
    member: bool = True


class Who(BaseModel):
    person: Optional[PersonOut] = None
    service: Optional[str] = None
    grants: list[GrantRow] = Field(default_factory=list)
    drift: list[Change] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    dry_run: bool
    bootstrap: bool = Field(
        False,
        description="True when this run imported a service's live state instead of changing it",
    )
    imported: list[str] = Field(
        default_factory=list, description="The services this run imported"
    )
    changes: list[Change] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    mapping: Optional[dict[str, Any]] = Field(
        None, description="The mapping a bootstrap proposes or stored"
    )
    note: Optional[str] = None
