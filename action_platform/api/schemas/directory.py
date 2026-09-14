from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Named(BaseModel):
    id: str
    name: str


class OrganizationRow(BaseModel):
    id: str
    name: str
    slug: str
    role: Optional[str] = None
    role_label: Optional[str] = None
    permissions: dict[str, bool]
    grantable_scopes: list[str]


class AppRef(BaseModel):
    id: str
    name: str
    registry_id: str


class Me(BaseModel):
    user: dict
    organization: Optional[dict] = None
    organizations: Optional[list[dict]] = None
    role: Optional[str] = None
    role_label: Optional[str] = None
    scope: Optional[list[str]] = None
    permissions: dict[str, bool]
    token: Optional[str] = None
    project: Optional[Named] = None
    app: Optional[AppRef] = None


class AppInProject(BaseModel):
    id: str
    name: str
    registry_id: str
    source_host_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None


class ProjectRow(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    team: Optional[Named] = None
    apps: list[AppInProject]
    organization: Optional[Named] = None


class TeamMemberRow(BaseModel):
    userId: str
    name: str
    email: str


class TeamRow(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    members: list[TeamMemberRow]
    projects: list[Named]


class MemberRow(BaseModel):
    user_id: str
    name: str
    email: str
    role: str
    role_label: str


class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = ""


class CreateTeamRequest(BaseModel):
    name: str
    description: Optional[str] = ""


class TeamMemberRequest(BaseModel):
    team_id: str
    user_id: str


class ProjectTeamRequest(BaseModel):
    project_id: str
    team_id: Optional[str] = None


class MemberRoleRequest(BaseModel):
    user_id: str
    role: str


class Created(BaseModel):
    id: str
    name: str
    slug: str


class Ok(BaseModel):
    ok: bool = True


class IssueRequest(BaseModel):
    scope: str
    name: Optional[str] = None


class Issued(BaseModel):
    token: str
    token_type: str = "Bearer"
    id: str
    scope: str
    expires_at: datetime
    organization: Optional[dict] = None
    organizations: Optional[list[dict]] = None
    project: Optional[Named] = None
    app: Optional[AppRef] = None


class RoleInfo(BaseModel):
    id: str
    label: str
    description: str
    permissions: list[str]
    grantable_scopes: list[str]


class PermissionInfo(BaseModel):
    id: str
    description: str


class ScopeInfo(BaseModel):
    id: str
    label: str
    description: str
    permissions: list[str]


class AccessCatalog(BaseModel):
    roles: list[RoleInfo]
    permissions: list[PermissionInfo]
    scopes: list[ScopeInfo]
    default_scopes: list[str]
