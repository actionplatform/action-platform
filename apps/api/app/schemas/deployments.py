from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class DeployRequest(BaseModel):
    stage: Optional[str] = None
    dry_run: bool = True
    version: Optional[str] = None


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
