"""What every provider module shares."""

import re
from datetime import datetime, timezone
from typing import Optional

from action_platform.api.services.credentials import Credentials
from action_platform.api.services.http import basic

RC = re.compile(r"-rc\.")


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    return (
        parsed.astimezone(timezone.utc).replace(tzinfo=None)
        if parsed.tzinfo
        else parsed
    )


def auth(creds: Credentials) -> dict[str, str]:
    if creds.kind == "github":
        return {
            "authorization": f"Bearer {creds.token}",
            "x-github-api-version": "2022-11-28",
        }

    if creds.kind == "bitbucket" and creds.username:
        return {"authorization": basic(creds.username, creds.token)}

    return {"authorization": f"Bearer {creds.token}"}
