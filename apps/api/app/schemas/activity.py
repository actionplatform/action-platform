from __future__ import annotations

from typing import Optional

from pydantic import BaseModel
from app.schemas.common import SourceCredentials


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
