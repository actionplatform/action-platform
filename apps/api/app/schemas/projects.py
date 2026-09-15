"""Projects and the apps registered in them, with what was imported for each."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.actions import InitRequest, InstallSpec
from app.schemas.common import Named


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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = ""


class ProjectTeamRequest(BaseModel):
    project_id: str
    team_id: Optional[str] = None


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
