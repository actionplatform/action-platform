"""Importing an organization from a code host: what the host shows, what to pick, what was queued."""

from typing import Optional

from pydantic import BaseModel


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
