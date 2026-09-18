"""Shapes many routes share."""

from pydantic import BaseModel
from typing import Optional


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
    job: Optional[str] = None


class AppRef(BaseModel):
    id: str
    name: str
    registry_id: str


class SourceCredentials(BaseModel):
    """A code-host token for this request and the identity commits are made with. Either half may be absent: identity alone still names the author."""

    kind: Optional[str] = None
    token: Optional[str] = None
    username: Optional[str] = None
    base_url: Optional[str] = None
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    owner: Optional[str] = None


class SourceSpec(BaseModel):
    name: str
    url: str
    ref: str = "main"
    credentials: Optional[SourceCredentials] = None


class PageMeta(BaseModel):
    total: int
    page: int
    per: int

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.per))


def page_bounds(page: int, per: int) -> tuple[int, int, int]:
    """(page, per, offset) with page ≥ 1 and 1 ≤ per ≤ 100."""
    per = max(1, min(int(per), 100))
    page = max(1, int(page))

    return page, per, (page - 1) * per
