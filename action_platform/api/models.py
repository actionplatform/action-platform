"""Response models. They are the contract the web app's TypeScript client is generated from."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Version(BaseModel):
    version: str


class MatrixProject(BaseModel):
    type: str
    stack: str
    template: str
    default: bool
    description: str


class MatrixCloud(BaseModel):
    name: str
    types: list[str]
    languages: list[str]
    description: str


class MatrixService(BaseModel):
    name: str
    providers: list[str]
    description: str


class Matrix(BaseModel):
    projects: list[MatrixProject]
    clouds: list[MatrixCloud]
    services: list[MatrixService]


class GitflowRules(BaseModel):
    kinds: list[str]
    protected: list[str]
    types: list[str]


class AppRow(BaseModel):
    id: str
    name: str
    url: str
    exists: bool
    language: Optional[str] = None
    type: Optional[str] = None
    last_version: Optional[str] = None
    branch: Optional[str] = None


class AppEntry(BaseModel):
    id: str
    name: str
    url: str
    path: str
    default_branch: str = ""


class AppMeta(BaseModel):
    name: str = ""
    type: Optional[str] = None
    stack: Optional[str] = None
    template: Optional[str] = None
    language: Optional[str] = None
    ci: Optional[str] = None


class AppDetail(BaseModel):
    id: str
    url: str
    default_branch: str = ""
    project: AppMeta
    source_host: dict[str, str]
    deploy: dict
    release: dict[str, str]
    services: dict
    last_version: Optional[str] = None
    branch: str
    latest_tag: Optional[str] = None
    clean: bool


class GitflowReport(BaseModel):
    branch: str
    problems: list[str]
    checked_commits: int
    ok: bool


class Commit(BaseModel):
    sha: str
    subject: str
    author: str
    date: str


class Branch(BaseModel):
    name: str
    date: str
    kind: Optional[str] = None
    protected: bool
    problem: Optional[str] = None


class ReleasePreview(BaseModel):
    current: str
    next: str
    changelog: str
    dry_run: bool


class DeployResult(BaseModel):
    target: str
    ok: bool
    version: str
    url: Optional[str] = None
    error: Optional[str] = None


class Diagnosis(BaseModel):
    ok: bool
    target: str
    status: str = ""
    version: Optional[str] = None
    url: Optional[str] = None
    details: dict[str, str] = {}


class SourceCredentials(BaseModel):
    kind: str
    token: str
    username: Optional[str] = None
    base_url: Optional[str] = None
    owner: Optional[str] = None


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
    push: bool = False
    private: bool = False
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
