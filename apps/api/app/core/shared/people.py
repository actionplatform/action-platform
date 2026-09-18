"""How a person is named on the platform: the display name, the email only when the account has none. Accounts on a code host keep their login."""

from __future__ import annotations

from typing import Any, Optional


def label(user: Optional[Any]) -> Optional[str]:
    if user is None:
        return None

    name = (getattr(user, "name", None) or "").strip()

    return name or getattr(user, "email", None) or None
