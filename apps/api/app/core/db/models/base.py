"""What every model shares: the declarative base, the column types, the clock."""

from datetime import datetime, timezone

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase

KEY = String(36)
SHORT = String(255)


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass
