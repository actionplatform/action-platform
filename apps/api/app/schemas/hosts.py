"""Code hosts, OAuth apps, the OAuth flow, GitHub Apps."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


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
