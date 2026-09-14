from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from action_platform.api.schemas.actions import InitRequest, InstallSpec


class AddAppToProject(BaseModel):
    url: str
    install: Optional[InstallSpec] = None


class AppAdded(BaseModel):
    id: str
    registry_id: str
    name: str
    installed: Optional[list[str]] = None


class InitAppInProject(InitRequest):
    source_host_id: Optional[str] = None
    template_source: Optional[str] = None


class AppInitialized(BaseModel):
    id: str
    registry_id: str
    name: str
    pushed: bool


class AppHostRequest(BaseModel):
    source_host_id: Optional[str] = None


class ReleaseRow(BaseModel):
    id: str
    tag: str
    name: Optional[str] = None
    body: Optional[str] = None
    url: Optional[str] = None
    author: Optional[str] = None
    sha: Optional[str] = None
    prerelease: bool
    draft: bool
    published_at: Optional[datetime] = None
    source: str
    synced_at: datetime


class PullRequestRow(BaseModel):
    id: str
    number: int
    title: str
    url: str
    author: Optional[str] = None
    head: str
    base: str
    state: str
    draft: bool
    created_at: datetime
    updated_at: datetime
    merged_at: Optional[datetime] = None
    source: str


class Imports(BaseModel):
    releases: list[ReleaseRow]
    pull_requests: list[PullRequestRow]
    errors: dict[str, Optional[str]] = {}


class TeamUpdate(BaseModel):
    name: str
    description: Optional[str] = ""


class InvitationRow(BaseModel):
    id: str
    email: str
    role: Optional[str] = None
    status: str
    expires_at: datetime
    created_at: datetime
    inviter: str


class InviteRequest(BaseModel):
    email: str
    role: str


class HostRow(BaseModel):
    id: str
    kind: str
    name: str
    base_url: Optional[str] = None
    username: Optional[str] = None
    default_owner: Optional[str] = None
    auth_kind: str
    login: Optional[str] = None
    created_at: datetime


class AddHostRequest(BaseModel):
    kind: str
    name: Optional[str] = ""
    token: str
    base_url: Optional[str] = ""
    username: Optional[str] = ""
    default_owner: Optional[str] = ""


class HostTokenRequest(BaseModel):
    token: str


class HostOwnerRequest(BaseModel):
    owner: str


class OAuthAppRow(BaseModel):
    provider: str
    label: str
    configured: bool
    client_id: Optional[str] = None
    base_url: Optional[str] = None
    slug: Optional[str] = None
    scopes: str
    callback_hint: str


class OAuthAppRequest(BaseModel):
    client_id: str
    client_secret: str
    base_url: Optional[str] = ""


class OAuthStartRequest(BaseModel):
    origin: str
    return_to: Optional[str] = "/settings"


class OAuthStarted(BaseModel):
    url: str


class OAuthCallbackRequest(BaseModel):
    origin: str
    code: Optional[str] = None
    state: Optional[str] = None
    installation_id: Optional[str] = None
    error: Optional[str] = None
    error_description: Optional[str] = None


class OAuthFinished(BaseModel):
    return_to: str
    query: dict[str, str]


class ManifestRequest(BaseModel):
    origin: str
    host: str
    return_to: Optional[str] = "/settings"
    github_org: Optional[str] = ""


class Manifest(BaseModel):
    target: str
    state: str
    manifest: dict[str, Any]


class ManifestCallbackRequest(BaseModel):
    code: Optional[str] = None
    state: Optional[str] = None


class GitAuthor(BaseModel):
    name: str
    email: str


class TemplateSourceRow(BaseModel):
    id: str
    name: str
    url: str
    ref: str
    source_host_id: Optional[str] = None
    created_at: datetime


class AddTemplateSource(BaseModel):
    name: str
    url: str
    ref: Optional[str] = ""


class Removed(BaseModel):
    removed: list[str] = []
    repositories: list[str] = []
