from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import Named


class SignUpRequest(BaseModel):
    name: str
    email: str
    password: str
    invitation_id: Optional[str] = None


class SignInRequest(BaseModel):
    email: str
    password: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    image: Optional[str] = None


class SessionOut(BaseModel):
    id: str
    token: str
    cookie: str
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    active_organization_id: Optional[str] = None


class OrganizationOut(BaseModel):
    id: str
    name: str
    slug: str


class Signed(BaseModel):
    user: UserOut
    session: SessionOut


class IdentityOut(BaseModel):
    user: UserOut
    session: SessionOut
    organization: Optional[OrganizationOut] = None
    organizations: list[OrganizationOut]
    role: Optional[str] = None
    grants: dict[str, bool]


class BrowserSessionOut(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    current: bool


class ActiveOrganizationRequest(BaseModel):
    organization_id: str


class CreateOrganizationRequest(BaseModel):
    name: str
    slug: str
    git_author_name: Optional[str] = None
    git_author_email: Optional[str] = None


class AddMemberRequest(BaseModel):
    organization_id: str
    name: str
    email: str
    password: str
    role: str


class MemberAdded(BaseModel):
    user_id: str
    existed: bool


class DeviceCodeRequest(BaseModel):
    client_id: Optional[str] = None
    scope: Optional[str] = None


class DeviceCodeOut(BaseModel):
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_in: int
    interval: int


class DeviceTokenRequest(BaseModel):
    grant_type: str
    device_code: str
    client_id: Optional[str] = None


class DeviceTokenOut(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    scope: str
    expires_in: int


class GrantIn(BaseModel):
    scope: list[str] = Field(default_factory=list)
    organization_id: Optional[str] = None
    project_id: Optional[str] = None
    app_id: Optional[str] = None


class GrantOut(GrantIn):
    pass


class DeviceRequestOut(BaseModel):
    status: str
    requested: list[str]
    grant: GrantOut
    client_id: Optional[str] = None
    expires_at: datetime


class DeviceDecision(BaseModel):
    user_code: str
    grant: Optional[GrantIn] = None


class DeviceDecisionOut(BaseModel):
    status: str


class IssueTokenRequest(BaseModel):
    name: str
    scope: str
    organization_id: Optional[str] = None
    project_id: Optional[str] = None
    app_id: Optional[str] = None


class TokenIssued(BaseModel):
    id: str
    token: str
    scope: list[str]
    expires_at: datetime


class TokenClientOut(BaseModel):
    name: str
    first_seen_at: datetime
    last_seen_at: datetime


class TokenOut(BaseModel):
    id: str
    name: str
    scope: list[str]
    organization: Optional[Named] = None
    project: Optional[Named] = None
    app: Optional[Named] = None
    created_at: datetime
    expires_at: datetime
    last_used_at: Optional[datetime] = None
    clients: list[TokenClientOut]


class VerifyTokenRequest(BaseModel):
    token: str
    client: Optional[str] = None


class TokenClaimsOut(BaseModel):
    id: str
    user: UserOut
    organization: Optional[OrganizationOut] = None
    organizations: list[OrganizationOut]
    all_organizations: bool
    scope: list[str]
    project_id: Optional[str] = None
    app_id: Optional[str] = None
    role: Optional[str] = None


class AuthStatus(BaseModel):
    configured: bool
    users: int
    organizations: int = 0


class OpenInvitation(BaseModel):
    id: str
    email: str
    role: str
    status: str
    expired: bool
    inviter: str
    organization: OrganizationOut
