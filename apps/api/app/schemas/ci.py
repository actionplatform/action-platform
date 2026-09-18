"""CI servers and the runs of an app."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CiHostRow(BaseModel):
    id: str
    kind: str
    name: str
    base_url: str
    username: Optional[str] = None
    created_at: datetime


class AddCiHostRequest(BaseModel):
    kind: str
    name: Optional[str] = ""
    base_url: str
    token: str
    username: Optional[str] = ""


class CiLink(BaseModel):
    kind: str
    ci_host_id: Optional[str] = None
    job: str = ""


class CiLinkRequest(BaseModel):
    ci_host_id: Optional[str] = None
    job: str = ""


class CiRunRow(BaseModel):
    id: str
    source: str
    number: int
    status: str
    name: Optional[str] = None
    url: Optional[str] = None
    branch: Optional[str] = None
    sha: Optional[str] = None
    trigger: Optional[str] = None
    started_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    synced_at: datetime


class CiRuns(BaseModel):
    link: CiLink
    runs: list[CiRunRow]
    error: Optional[str] = None
    total: int = 0
    page: int = 1
    per: int = 10
