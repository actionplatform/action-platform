"""Importing an organization from a code host: what the host shows, what to pick, what was queued."""

from typing import Optional, Union

from pydantic import BaseModel


class ProjectPick(BaseModel):
    number: Union[int, str]
    project_id: Optional[str] = None


class ImportRequest(BaseModel):
    host_id: str
    organization: str
    repositories: list[str] = []
    projects: list[ProjectPick] = []
    teams: list[str] = []
    people: list[str] = []
    role: str = "developer"
    roles: dict[str, str] = {}
    people_roles: dict[str, str] = {}
    project_id: Optional[str] = None


class ImportQueued(BaseModel):
    job: str
    poll: str


class ImportOrganization(BaseModel):
    login: str
    name: str
    kind: str
    avatar: Optional[str] = None


class ImportOrganizations(BaseModel):
    organizations: list[ImportOrganization]
    install_url: Optional[str] = None


class ImportRepository(BaseModel):
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


class ImportProject(BaseModel):
    number: Union[int, str]
    title: str
    description: Optional[str] = None
    closed: bool
    url: Optional[str] = None
    repositories: list[str]
    exists: bool


class ImportTeam(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    members: list[str]
    repositories: list[str]
    exists: bool


class ImportPerson(BaseModel):
    login: str
    name: str
    email: Optional[str] = None
    avatar: Optional[str] = None
    role: str = "member"
    status: str


class ImportPreview(BaseModel):
    organization: str
    host_kind: str = "github"
    repositories: list[ImportRepository]
    projects: list[ImportProject] = []
    teams: list[ImportTeam]
    people: list[ImportPerson]
    problems: list[str] = []
    limits: list[str] = []
