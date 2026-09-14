"""Small helpers every service shares."""

import re
import uuid
from datetime import datetime, timezone
from typing import Optional

REPO_IN_URL = re.compile(r"[:/]([^/:]+/[^/]+?)(?:\.git)?$")


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_id() -> str:
    return str(uuid.uuid4())


def slugify(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.strip().lower())).strip(
        "-"
    )


def repo_from_url(url: str) -> Optional[str]:
    match = REPO_IN_URL.search(url or "")

    return match.group(1) if match else None


def kind_of_url(url: str) -> Optional[str]:
    if "github.com" in url:
        return "github"

    if "gitlab" in url:
        return "gitlab"

    if "bitbucket.org" in url:
        return "bitbucket"

    return None
