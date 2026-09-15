"""Naive UTC timestamps, the way the database stores them."""

from datetime import datetime, timezone
from typing import Optional


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_utc(value: Optional[str]) -> Optional[datetime]:
    """An ISO timestamp from a provider, as naive UTC."""
    if not value:
        return None

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    return (
        parsed.astimezone(timezone.utc).replace(tzinfo=None)
        if parsed.tzinfo
        else parsed
    )
