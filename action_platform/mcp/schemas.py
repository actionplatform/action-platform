"""What every tool answers with, as pydantic models: the client gets an output schema next to the input one, and the agent reads typed fields instead of guessing at a dict."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class Open(BaseModel):
    """A row the platform shapes: the fields named here are guaranteed, the rest travel as they come."""

    model_config = ConfigDict(extra="allow")


class MatrixProject(BaseModel):
    type: str
    stack: Optional[str] = None
    template: str
    default: bool = False
    description: str = ""


class MatrixCloud(BaseModel):
    name: str
    types: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    description: str = ""


class MatrixService(BaseModel):
    name: str
    providers: list[str] = Field(default_factory=list)
    description: str = ""


class Matrix(Open):
    projects: list[MatrixProject]
    clouds: list[MatrixCloud]
    services: list[MatrixService]


class Generated(BaseModel):
    path: str
    template: str
    cloud: Optional[str] = None


class Pushed(BaseModel):
    remote: str


class CloudSet(BaseModel):
    path: str
    deploy_target: str


class ServiceAdded(BaseModel):
    path: str
    provider: str


class InstallPlan(BaseModel):
    path: str
    language: str
    type: str
    ci: str
    created: list[str]
    kept: list[str]
    hooks_installed: bool
    hooks_preserved: list[str]
    hooks_skipped: Optional[str] = None
    dry_run: bool


class ProjectInfo(Open):
    name: Optional[str] = None
    type: Optional[str] = None
    language: Optional[str] = None


class GitflowRules(BaseModel):
    kinds: list[str]
    protected: list[str]
    base: dict[str, list[str]]
    merge_into: dict[str, str]
    branch_name: str
    commit: str
    exceptions_on_protected: list[str]


class BranchStarted(BaseModel):
    branch: str
    base: str
    pushed: bool


class GitflowReport(BaseModel):
    branch: str
    ok: bool
    checked_commits: int
    problems: list[str]


class PullRequestPlan(BaseModel):
    head: str
    base: str
    title: str
    body: str
    commits: list[str]


class PullRequestOpened(BaseModel):
    number: int
    url: str


class HooksInstalled(BaseModel):
    installed: bool
    directory: Optional[str] = None
    preserved: list[str]
    skipped: Optional[str] = None


class ReleasePlan(BaseModel):
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


class RolledBack(BaseModel):
    rolled_back_to: str


class DeployTargetRow(Open):
    name: str
    kind: str
    run_by: str
    stages: list[str] = []
    workflow: Optional[str] = None
    job: Optional[str] = None


class DeploymentRow(Open):
    id: str
    target: str
    kind: str
    stage: Optional[str] = None
    version: str
    status: str
    executor: str
    url: Optional[str] = None
    actor: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    verified_at: Optional[str] = None


class Deployments(Open):
    targets: list[DeployTargetRow]
    deployments: list[DeploymentRow]
    error: Optional[str] = None


class Diagnosis(BaseModel):
    target: str
    ok: bool
    status: str
    url: Optional[str] = None
    details: dict[str, str]


class WhoAmI(BaseModel):
    server: str
    user: Optional[dict[str, Any]] = None
    organization: Optional[dict[str, Any]] = None
    organizations: Optional[list[dict[str, Any]]] = None
    spans_every_organization: bool
    role: Optional[str] = None
    scope: Optional[list[str]] = None
    limited_to: dict[str, Optional[dict[str, Any]]]
    can: dict[str, bool]


class OrganizationRow(Open):
    id: str
    name: str
    slug: str
    role: Optional[str] = None
    role_label: Optional[str] = None
    permissions: dict[str, bool] = Field(default_factory=dict)
    grantable_scopes: list[str] = Field(default_factory=list)


class Named(BaseModel):
    id: str
    name: str


class AppRef(Open):
    id: str
    name: str
    registry_id: str


class ProjectRow(Open):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    team: Optional[Named] = None
    apps: list[AppRef] = Field(default_factory=list)
    organization: Optional[Named] = None


class TeamRow(Open):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    members: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[Named] = Field(default_factory=list)


class MemberRow(Open):
    user_id: str
    name: str
    email: str
    role: str
    role_label: Optional[str] = None


class Created(Open):
    id: str
    name: str
    slug: Optional[str] = None


class Ok(Open):
    ok: bool = True


class CurrentContext(BaseModel):
    directory: str
    remote: Optional[str] = None
    branch: Optional[str] = None
    organization: Optional[dict[str, Any]] = None
    project: Optional[dict[str, Any]] = None
    app: Optional[dict[str, Any]] = None
    role: Optional[str] = None
    scope: Optional[list[str]] = None
    can: Optional[dict[str, bool]] = None
    hint: Optional[str] = None


class AppRow(Open):
    id: str
    name: str
    url: str
    exists: bool = True
    language: Optional[str] = None
    type: Optional[str] = None
    last_version: Optional[str] = None
    branch: Optional[str] = None


class AppAdded(Open):
    id: str
    registry_id: str
    name: str
    installed: Optional[list[str]] = None


class Removed(Open):
    removed: list[str] = Field(default_factory=list)
    repositories: list[str] = Field(default_factory=list)


class AppEntry(Open):
    id: str
    name: str
    url: str
    default_branch: str = ""
    installed: Optional[list[str]] = None


class AppDetail(Open):
    id: str
    url: str
    default_branch: str = ""
    project: dict[str, Any] = Field(default_factory=dict)
    deploy: dict[str, Any] = Field(default_factory=dict)
    services: dict[str, Any] = Field(default_factory=dict)
    last_version: Optional[str] = None
    branch: Optional[str] = None
    latest_tag: Optional[str] = None
    clean: Optional[bool] = None


class Commit(Open):
    sha: str
    subject: str
    author: Optional[str] = None
    date: Optional[str] = None


class BranchRow(Open):
    name: str
    date: Optional[str] = None
    kind: Optional[str] = None
    protected: bool = False
    stable: bool = False
    problem: Optional[str] = None


class ReleaseRow(Open):
    tag: str
    version: str
    date: Optional[str] = None
    sha: Optional[str] = None
    subject: Optional[str] = None
    prerelease: bool = False
    latest: bool = False


class ReleasePreview(Open):
    current: str
    next: str
    changelog: str
    branch: Optional[str] = None
    prerelease: bool = False
    dry_run: bool


class ManifestText(BaseModel):
    content: str


class ConfigurationChanged(Open):
    installed: Optional[list[str]] = None


class Committed(Open):
    sha: str
    branch: str
    pushed: bool
    pull_request: Optional[dict[str, Any]] = None


class Initialized(Open):
    id: str
    registry_id: str
    name: str
    pushed: bool
