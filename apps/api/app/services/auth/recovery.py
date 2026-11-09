"""Password recovery: a single-use link sent by email, stored only as a hash, that sets a new password and closes every session."""

import hashlib
import secrets
from datetime import timedelta
from html import escape
from typing import Optional

from sqlalchemy import delete, select

from app.core.auth.passwords import hash_password
from app.core.db.models import Account, Session, User, Verification
from app.core.shared.mail import Mail
from app.services.auth.base import PASSWORD_MIN, PROVIDER, AuthBase, new_id, now
from app.services.auth.errors import AuthError

RESET_TTL = timedelta(minutes=30)
RESET_PREFIX = "password-reset:"


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def reset_mail(user: User, link: str) -> Mail:
    minutes = int(RESET_TTL.total_seconds() // 60)
    text = (
        f"Hi {user.name},\n\n"
        "Someone asked to reset the password of your Action Platform account. "
        f"Open this link within {minutes} minutes to choose a new one:\n\n"
        f"{link}\n\n"
        "If it was not you, ignore this email: your password stays the same."
    )
    html = (
        f"<p>Hi {escape(user.name)},</p>"
        "<p>Someone asked to reset the password of your Action Platform account. "
        f"Open this link within {minutes} minutes to choose a new one:</p>"
        f'<p><a href="{escape(link)}">Reset your password</a></p>'
        "<p>If it was not you, ignore this email: your password stays the same.</p>"
    )

    return Mail(user.email, "Reset your Action Platform password", text, html)


class Recovery(AuthBase):
    def request_password_reset(self, email: str) -> Optional[tuple[User, str]]:
        """The user and a fresh reset token when `email` belongs to an account with a password; None otherwise, so the caller answers the same either way."""
        user = self.db.scalar(select(User).where(User.email == email.strip().lower()))

        if user is None or self._credential(user.id) is None:
            return None

        identifier = f"{RESET_PREFIX}{user.id}"
        self.db.execute(
            delete(Verification).where(Verification.identifier == identifier)
        )
        token = secrets.token_urlsafe(32)
        moment = now()
        self.db.add(
            Verification(
                id=new_id(),
                identifier=identifier,
                value=_digest(token),
                expires_at=moment + RESET_TTL,
                created_at=moment,
                updated_at=moment,
            )
        )
        self.db.flush()

        return user, token

    def reset_password(self, token: str, password: str) -> User:
        if len(password) < PASSWORD_MIN:
            raise AuthError(
                "weak_password", f"password needs at least {PASSWORD_MIN} characters"
            )

        row = self.db.scalar(
            select(Verification).where(
                Verification.value == _digest(token),
                Verification.identifier.startswith(RESET_PREFIX),
            )
        )

        if row is None or row.expires_at < now():
            if row is not None:
                self.db.delete(row)
                self.db.flush()

            raise AuthError("invalid_token", "this link is invalid or has expired")

        user_id = row.identifier.removeprefix(RESET_PREFIX)
        user = self.db.get(User, user_id)
        account = self._credential(user_id)

        if user is None or account is None:
            self.db.delete(row)
            self.db.flush()

            raise AuthError("invalid_token", "this link is invalid or has expired")

        moment = now()
        account.password = hash_password(password)
        account.updated_at = moment
        self.db.delete(row)
        self.db.execute(delete(Session).where(Session.user_id == user_id))
        self.db.flush()

        return user

    def _credential(self, user_id: str) -> Optional[Account]:
        return self.db.scalar(
            select(Account).where(
                Account.user_id == user_id, Account.provider_id == PROVIDER
            )
        )
