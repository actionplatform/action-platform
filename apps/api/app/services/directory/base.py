"""What every directory module shares: the session, the sealer, the error and the constants."""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Optional

from sqlalchemy.orm import Session as DbSession

from action_platform.core.exception import ActionPlatformError
from app.core.auth.crypto import Sealer

DEFAULT_GIT_AUTHOR = ("Action Platform", "cloud@actionplatform.io")
REFRESH_MARGIN = timedelta(seconds=60)
INVITATION_TTL = timedelta(days=7)
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GIT_URL = re.compile(r"^(https?://|git@|ssh://|file://)")
PROVIDERS = ("github", "gitlab", "bitbucket")
HOST_KINDS = ("github", "gitlab", "bitbucket", "generic")
HOST_LABELS = {
    "github": "GitHub",
    "gitlab": "GitLab",
    "bitbucket": "Bitbucket",
    "generic": "Git",
}


class DirectoryError(ActionPlatformError):
    pass


class DirectoryBase:
    def __init__(self, db: DbSession, sealer: Optional[Sealer] = None) -> None:
        self.db = db
        self.sealer = sealer
