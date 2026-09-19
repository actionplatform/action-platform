from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AppRow(BaseModel):
    id: str
    name: str
    url: str
    exists: bool
    language: Optional[str] = None
    type: Optional[str] = None
    deploy_target: Optional[str] = None
    last_version: Optional[str] = None
    branch: Optional[str] = None


class AppEntry(BaseModel):
    id: str
    name: str
    url: str
    path: str
    default_branch: str = ""
    installed: Optional[list[str]] = None


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
    snapshot_at: Optional[datetime] = None


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
    sha: Optional[str] = None
    kind: Optional[str] = None
    protected: bool
    stable: bool = False
    problem: Optional[str] = None


class Release(BaseModel):
    tag: str
    version: str
    date: str
    sha: str
    subject: str
    prerelease: bool
    latest: bool
