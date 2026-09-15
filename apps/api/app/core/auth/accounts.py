"""Sign up and sign in: users and their passwords."""

from typing import Optional

from sqlalchemy import func, select

from app.core.auth.errors import (
    AuthError,
    Forbidden,
)
from app.core.auth.passwords import hash_password, verify_password
from app.core.db.models import (
    Account,
    Invitation,
    Session,
    User,
)
from app.core.auth.base import (
    PASSWORD_MIN,
    PROVIDER,
    AuthBase,
    new_id,
    now,
)


class Accounts(AuthBase):
    def user_count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(User)) or 0

    def sign_up(
        self, name: str, email: str, password: str, invitation_id: Optional[str] = None
    ) -> tuple[User, Session]:
        email = email.strip().lower()
        name = name.strip()

        if not name or not email:
            raise AuthError("invalid", "name and email are required")

        if len(password) < PASSWORD_MIN:
            raise AuthError(
                "weak_password", f"password needs at least {PASSWORD_MIN} characters"
            )

        invitation = self.db.get(Invitation, invitation_id) if invitation_id else None

        if self.user_count() > 0:
            if (
                invitation is None
                or invitation.status != "pending"
                or invitation.expires_at < now()
            ):
                raise Forbidden("sign-up is closed: an owner has to invite you")

            if invitation.email.lower() != email:
                raise Forbidden("this invitation was sent to another address")

        if self.db.scalar(select(User).where(User.email == email)):
            raise AuthError("exists", "an account with this email already exists", 409)

        moment = now()
        user = User(
            id=new_id(),
            name=name,
            email=email,
            email_verified=False,
            created_at=moment,
            updated_at=moment,
        )
        self.db.add(user)
        self.db.add(
            Account(
                id=new_id(),
                account_id=user.id,
                provider_id=PROVIDER,
                user_id=user.id,
                password=hash_password(password),
                created_at=moment,
                updated_at=moment,
            )
        )
        self.db.flush()

        return user, self.open_session(user)

    def sign_in(
        self,
        email: str,
        password: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> tuple[User, Session]:
        user = self.db.scalar(select(User).where(User.email == email.strip().lower()))
        account = (
            self.db.scalar(
                select(Account).where(
                    Account.user_id == user.id, Account.provider_id == PROVIDER
                )
            )
            if user
            else None
        )

        if (
            user is None
            or account is None
            or not verify_password(account.password, password)
        ):
            raise AuthError("invalid_credentials", "email or password is wrong", 401)

        return user, self.open_session(user, ip, user_agent)
