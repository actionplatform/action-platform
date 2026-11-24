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


class ConnectionRow(BaseModel):
    kind: str
    label: str
    configured: bool
    connected: bool
    login: Optional[str] = None
    base_url: Optional[str] = None
    scopes: Optional[list[str]] = None
    asked: list[str]
    missing: list[str]
    expires_at: Optional[datetime] = None
    connected_at: Optional[datetime] = None


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


class GitHubAppManifestRequest(BaseModel):
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


class PluginOption(BaseModel):
    key: str
    label: str
    kind: str = "text"
    help: str = ""
    required: bool = False
    action_label: str = ""
    action_url: str = ""
    action_copy: str = ""
    default: str = ""


class PluginRow(BaseModel):
    slug: str
    name: str = ""
    package: str = ""
    version: str = ""
    description: str = ""
    min_core: str = ""
    needs: list[str] = []
    options: list[PluginOption] = []
    events: bool = False
    error: Optional[str] = None


class Plugins(BaseModel):
    plugins: list[PluginRow]


class PluginDelivery(BaseModel):
    id: str
    event: str
    route: str
    project: str = ""
    app: str = ""
    url: Optional[str] = None
    status: str
    attempts: int = 0
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class PluginDeliveries(BaseModel):
    deliveries: list[PluginDelivery]


class PluginOptions(BaseModel):
    options: dict[str, Any]
    secrets: list[str] = []


class WebhookInfo(BaseModel):
    url: str
    configured: bool
    kind: str


class WebhookSecret(BaseModel):
    url: str
    secret: str
    kind: str


class WebhookReceived(BaseModel):
    event: str
    repo: Optional[str] = None
    queued: list[str] = []
