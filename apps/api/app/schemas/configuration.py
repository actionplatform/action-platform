from __future__ import annotations

from typing import Optional

from pydantic import BaseModel
from app.schemas.common import SourceCredentials, SourceSpec


class CloudRequest(BaseModel):
    target: str
    source: Optional[SourceSpec | str] = None


class ServiceRequest(BaseModel):
    name: str
    provider: Optional[str] = None
    source: Optional[SourceSpec | str] = None


class AppConfigBody(BaseModel):
    content: str
    mirrored: Optional[bool] = None


class Changes(BaseModel):
    files: list[str]
    clean: bool


class CommitBranch(BaseModel):
    kind: str
    code: str
    slug: Optional[str] = None


class CommitPullRequest(BaseModel):
    number: int
    url: str


class CommitRequest(BaseModel):
    message: str
    push: bool = True
    branch: Optional[CommitBranch] = None
    pull_request: bool = False
    credentials: Optional[SourceCredentials] = None


class CommitResult(BaseModel):
    sha: str
    branch: str
    pushed: bool
    pull_request: Optional[CommitPullRequest] = None
