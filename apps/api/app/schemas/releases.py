from __future__ import annotations

from typing import Optional

from pydantic import BaseModel
from app.schemas.common import SourceCredentials


class ReleaseRequest(BaseModel):
    level: str = "patch"
    dry_run: bool = True
    branch: Optional[str] = None
    component: Optional[str] = None
    name: Optional[str] = None
    notes: Optional[str] = None
    latest: bool = True
    credentials: Optional[SourceCredentials] = None


class NextVersion(BaseModel):
    current: str
    next: str
    branch: str
    prerelease: bool


class ReleasePreview(BaseModel):
    current: str
    next: str
    changelog: str
    branch: str
    prerelease: bool
    dry_run: bool
