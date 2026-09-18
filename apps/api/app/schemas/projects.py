"""Projects and the apps registered in them, with what was imported for each."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import Named
from app.schemas.common import SourceCredentials, SourceSpec


class InstallSpec(BaseModel):
    type: str = "web"
    language: Optional[str] = None
    ci: Optional[str] = None


class AddAppRequest(BaseModel):
    url: str
    name: Optional[str] = None
    install: Optional[InstallSpec] = None
    credentials: Optional[SourceCredentials] = None


class SyncRequest(BaseModel):
    credentials: Optional[SourceCredentials] = None
    reset: bool = False


class InitRequest(BaseModel):
    type: str
    stack: Optional[str] = None
    template: Optional[str] = None
    name: str
    description: str = ""
    package_name: Optional[str] = None
    github_owner: Optional[str] = None
    ci: Optional[str] = None
    cloud: Optional[str] = None
    git_init: bool = True
    push: bool = True
    private: bool = False
    source: Optional[SourceSpec] = None
    credentials: Optional[SourceCredentials] = None


class InitResult(BaseModel):
    id: str
    name: str
    path: str
    url: str
    template: str
    cloud: Optional[str] = None
    pushed: bool


class PushRequest(BaseModel):
    private: bool = False
    credentials: Optional[SourceCredentials] = None


class PushResult(BaseModel):
    id: str
    url: str


class Installed(BaseModel):
    installed: list[str]


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
    tearing_down: bool = False


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
    component: str = ""
    version: str = ""
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
    readiness: dict[str, str] = {}


class ReadinessCheck(BaseModel):
    id: str
    ok: bool
    detail: str = ""
    level: str = "target"
    severity: str = "error"
    fix: Optional[str] = None
    target: Optional[str] = None


class ReadinessRow(BaseModel):
    stage: str
    status: str
    verdict: str
    ok: Optional[bool] = None
    checks: list[ReadinessCheck] = []
    job_id: Optional[str] = None
    checked_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ReadinessRequest(BaseModel):
    stage: Optional[str] = None


class ReadinessQueued(BaseModel):
    jobs: list[str]
    readiness: list[ReadinessRow]


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


class ReleasePage(BaseModel):
    items: list[ReleaseRow]
    total: int
    page: int
    per: int


class PullRequestPage(BaseModel):
    items: list[PullRequestRow]
    total: int
    page: int
    per: int
