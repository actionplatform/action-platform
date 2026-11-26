"""Git-flow enforced on the code host: each rule's state, the app's setting and the organization's default."""

from typing import Optional

from pydantic import BaseModel

from app.schemas.common import UtcDateTime


class ProtectionRule(BaseModel):
    rule: str
    label: str
    mode: str
    detail: str = ""


class ProtectionFix(BaseModel):
    label: str
    url: str


class ProtectionState(BaseModel):
    host: str
    active: bool
    branches: list[str] = []
    checks: list[str] = []
    rules: list[ProtectionRule] = []
    drift: list[str] = []
    error: Optional[str] = None
    changed_by: Optional[str] = None
    bypass: Optional[str] = None
    fix: Optional[ProtectionFix] = None


class Protection(BaseModel):
    enforce: bool
    source: str
    organization_default: bool
    branches: list[str] = []
    state: Optional[ProtectionState] = None
    checked_at: Optional[UtcDateTime] = None
    applied_at: Optional[UtcDateTime] = None
    job_id: Optional[str] = None


class ProtectionRequest(BaseModel):
    enforce: Optional[bool] = None


class ProtectionDefault(BaseModel):
    enforce: bool
