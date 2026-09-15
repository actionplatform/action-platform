"""Shapes many routes share."""

from pydantic import BaseModel


class Named(BaseModel):
    id: str
    name: str


class Ok(BaseModel):
    ok: bool = True


class Created(BaseModel):
    id: str
    name: str
    slug: str


class Removed(BaseModel):
    removed: list[str] = []
    repositories: list[str] = []


class AppRef(BaseModel):
    id: str
    name: str
    registry_id: str
