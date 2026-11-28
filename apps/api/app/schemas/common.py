"""Shapes many routes share."""

from datetime import datetime, timezone
from typing import Annotated, Generic, Optional, TypeVar, Union

from pydantic import BaseModel, PlainSerializer


def utc(value: datetime) -> datetime:
    """A timestamp with its UTC offset; naive values are UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


UtcDateTime = Annotated[
    datetime, PlainSerializer(utc, return_type=datetime, when_used="json")
]


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
    organization_id: Optional[str] = None


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


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    per: int


def paged(rows: list[T], page: Optional[int], per: int) -> Union[list[T], Page[T]]:
    """The rows as they are, or one `Page` of them when the caller asks for a `page`."""
    if page is None:
        return rows

    page, per, offset = page_bounds(page, per)

    return Page(items=rows[offset : offset + per], total=len(rows), page=page, per=per)
