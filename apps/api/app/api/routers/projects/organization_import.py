"""Import a code-host organization into the platform: repositories, teams and people."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from action_platform.core.exception import ActionPlatformError
from app.api.dependencies import (
    CallerDep,
    OrgDep,
    QueueDep,
    WritesDep,
    allowed,
)
from app.repositories.registry import Registry
from app.repositories.source import get_registry
from app.services.directory import DirectoryWrites
from app.services.organization_import import OrganizationImport, client

router = APIRouter(prefix="/api/v1/import", tags=["import"])
JOB_KIND = "import_github"


class ProjectPick(BaseModel):
    number: int
    project_id: Optional[str] = None


class ImportRequest(BaseModel):
    host_id: str
    organization: str
    repositories: list[str] = []
    projects: list[ProjectPick] = []
    teams: list[str] = []
    people: list[str] = []
    role: str = "developer"
    project_id: Optional[str] = None


class ImportQueued(BaseModel):
    job: str
    poll: str


class GithubOrganization(BaseModel):
    login: str
    name: str
    kind: str
    avatar: Optional[str] = None


class GithubOrganizations(BaseModel):
    organizations: list[GithubOrganization]
    install_url: Optional[str] = None


class GithubRepository(BaseModel):
    full_name: str
    name: str
    description: Optional[str] = None
    private: bool
    archived: bool
    fork: bool
    language: Optional[str] = None
    default_branch: str
    url: str
    pushed_at: Optional[str] = None
    imported_as: Optional[str] = None


class GithubProject(BaseModel):
    number: int
    title: str
    description: Optional[str] = None
    closed: bool
    url: Optional[str] = None
    repositories: list[str]
    exists: bool


class GithubTeam(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    members: list[str]
    repositories: list[str]
    exists: bool


class GithubPerson(BaseModel):
    login: str
    name: str
    email: Optional[str] = None
    avatar: Optional[str] = None
    status: str


class GithubPreview(BaseModel):
    organization: str
    repositories: list[GithubRepository]
    projects: list[GithubProject] = []
    teams: list[GithubTeam]
    people: list[GithubPerson]
    problems: list[str] = []


def github_credentials(writes: DirectoryWrites, org, host_id: str):
    host = writes.host(org.id, host_id)

    if host is None:
        raise HTTPException(404, "host not found")

    if host.kind != "github":
        raise HTTPException(400, "only GitHub hosts can be imported for now")

    try:
        creds = writes.credentials_for(org.id, host_id)
    except ActionPlatformError as e:
        raise HTTPException(400, f"{e}; reconnect the host") from e

    if creds is None:
        raise HTTPException(400, "this host has no credentials; reconnect it")

    return creds


@router.get("/github/organizations")
def github_organizations(
    host: str,
    org: OrgDep,
    caller: CallerDep,
    writes: WritesDep,
) -> GithubOrganizations:
    allowed(caller, org, "org.manage")
    creds = github_credentials(writes, org, host)
    github_app = writes.oauth_app("github")

    try:
        organizations = client.GithubDirectory(creds).organizations()
    except ActionPlatformError as e:
        raise HTTPException(502, str(e)) from e

    return GithubOrganizations(
        organizations=organizations,
        install_url=(
            f"https://github.com/apps/{github_app.slug}/installations/select_target"
            if github_app and github_app.slug
            else None
        ),
    )


@router.get("/github/organizations/{login}")
def github_organization(
    login: str,
    host: str,
    org: OrgDep,
    caller: CallerDep,
    writes: WritesDep,
    registry: Registry = Depends(get_registry),
) -> GithubPreview:
    allowed(caller, org, "org.manage")
    creds = github_credentials(writes, org, host)

    try:
        return OrganizationImport(writes, org.id, registry).preview(creds, login)
    except ActionPlatformError as e:
        raise HTTPException(502, str(e)) from e


@router.post("/github", status_code=202)
def import_github(
    body: ImportRequest,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    writes: WritesDep,
    queue: QueueDep,
) -> ImportQueued:
    allowed(caller, org, "org.manage")
    github_credentials(writes, org, body.host_id)

    if not (body.repositories or body.projects or body.teams or body.people):
        raise HTTPException(400, "pick at least one repository, team or person")

    job = queue.enqueue(
        JOB_KIND,
        {
            **body.model_dump(),
            "organization_id": org.id,
            "inviter_id": caller.user.id,
        },
        organization_id=org.id,
    )

    return ImportQueued(job=job.id, poll=f"/api/v1/jobs/{job.id}")
