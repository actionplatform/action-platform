from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from action_platform.api.schemas.actions import SourceSpec


class Version(BaseModel):
    version: str


class MatrixProject(BaseModel):
    type: str
    stack: str
    template: str
    default: bool
    description: str
    source: str = "official"


class MatrixCloud(BaseModel):
    name: str
    types: list[str]
    languages: list[str]
    description: str
    source: str = "official"


class MatrixService(BaseModel):
    name: str
    providers: list[str]
    description: str
    source: str = "official"


class SourcesRequest(BaseModel):
    sources: list[SourceSpec] = []


class SourceStatus(BaseModel):
    name: str
    url: str
    ref: str
    ok: bool
    error: Optional[str] = None
    projects: int = 0
    clouds: int = 0
    services: int = 0


class Matrix(BaseModel):
    projects: list[MatrixProject]
    clouds: list[MatrixCloud]
    services: list[MatrixService]
    sources: list[SourceStatus] = []


class GitflowRules(BaseModel):
    kinds: list[str]
    protected: list[str]
    types: list[str]
