"""What every part of the auth service shares: the database session, the secrets, the constants, the identity shape."""

import re
import secrets
import string
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session as DbSession

from app.core.auth.secrets import Secrets
from app.core.db.models import (
    Organization,
    Session,
    User,
)

SESSION_TTL = timedelta(days=7)
SESSION_REFRESH_AFTER = timedelta(days=1)
DEVICE_TTL = timedelta(minutes=10)
DEVICE_INTERVAL = 3
TOKEN_TTL = timedelta(days=90)
ADMIN_TOKEN_TTL = timedelta(days=30)
ISSUER = "action-platform"
AUDIENCE = "action-platform/api/v1"
PASSWORD_MIN = 8
USER_CODE_ALPHABET = string.ascii_uppercase + string.digits
PROVIDER = "credential"
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_id() -> str:
    return str(uuid.uuid4())


def _token(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits

    return "".join(secrets.choice(alphabet) for _ in range(length))


@dataclass(frozen=True)
class Identity:
    """Who a request is: the user, the session it rides on, the organization it acts in and the role there."""

    user: User
    session: Optional[Session]
    organization: Optional[Organization]
    role: Optional[str]


class AuthBase:
    def __init__(
        self, db: DbSession, secrets: Secrets, verification_uri: str = "/device"
    ) -> None:
        self.db = db
        self.secrets = secrets
        self.verification_uri = verification_uri
