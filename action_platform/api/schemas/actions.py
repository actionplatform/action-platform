from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class SourceCredentials(BaseModel):
    kind: str
    token: str
    username: Optional[str] = None
    base_url: Optional[str] = None
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    owner: Optional[str] = None


class SourceSpec(BaseModel):
    name: str
    url: str
    ref: str = "v1"
    credentials: Optional[SourceCredentials] = None


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


class ReleaseRequest(BaseModel):
    level: str = "patch"
    dry_run: bool = True
    branch: Optional[str] = None
    component: Optional[str] = None
    credentials: Optional[SourceCredentials] = None


class DeployRequest(BaseModel):
    stage: Optional[str] = None
    dry_run: bool = True


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


class ReleasePreview(BaseModel):
    current: str
    next: str
    changelog: str
    branch: str
    prerelease: bool
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


class StartBranchRequest(BaseModel):
    kind: str
    code: str
    slug: Optional[str] = None
    push: bool = True
    credentials: Optional[SourceCredentials] = None


class BranchResult(BaseModel):
    branch: str
    base: str
    pushed: bool


class CheckoutRequest(BaseModel):
    branch: str


class PullRequestRequest(BaseModel):
    base: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    draft: bool = False
    credentials: Optional[SourceCredentials] = None


class PullRequestProposal(BaseModel):
    head: str
    base: str
    title: str
    body: str
    commits: list[str]


class PullRequestResult(BaseModel):
    number: int
    url: str


class CloudRequest(BaseModel):
    target: str
    source: Optional[SourceSpec] = None


class ServiceRequest(BaseModel):
    name: str
    provider: Optional[str] = None
    source: Optional[SourceSpec] = None


class ManifestBody(BaseModel):
    content: str


class Installed(BaseModel):
    installed: list[str]


class Changes(BaseModel):
    files: list[str]
    clean: bool


class CommitBranch(BaseModel):
    kind: str
    code: str
    slug: Optional[str] = None


class CommitRequest(BaseModel):
    message: str
    push: bool = False
    branch: Optional[CommitBranch] = None
    pull_request: bool = False
    credentials: Optional[SourceCredentials] = None


class CommitPullRequest(BaseModel):
    number: int
    url: str


class CommitResult(BaseModel):
    sha: str
    branch: str
    pushed: bool
    pull_request: Optional[CommitPullRequest] = None
