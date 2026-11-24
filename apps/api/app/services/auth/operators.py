"""What an operator does from inside the API container: list, create, disable and enable users."""

import secrets
from typing import Optional

from sqlalchemy import select

from action_platform.core.access import ROLES
from app.core.db.models import Member, Organization, User
from app.services.auth.base import EMAIL, PASSWORD_MIN, AuthBase, new_id, now
from app.services.auth.errors import AuthError


class Operators(AuthBase):
    def users(self) -> list[tuple[User, list[tuple[Organization, str]]]]:
        """Every user with the organizations they belong to and their role there, oldest first."""
        users = self.db.scalars(select(User).order_by(User.created_at)).all()
        memberships: dict[str, list[tuple[Organization, str]]] = {
            u.id: [] for u in users
        }

        for member, organization in self.db.execute(
            select(Member, Organization)
            .join(Organization, Organization.id == Member.organization_id)
            .order_by(Organization.name)
        ):
            memberships.setdefault(member.user_id, []).append(
                (organization, member.role)
            )

        return [(u, memberships[u.id]) for u in users]

    def user_by_email(self, email: str) -> User:
        user = self.db.scalar(select(User).where(User.email == email.strip().lower()))

        if user is None:
            raise AuthError("not_found", f"no user with the email {email.strip()}", 404)

        return user

    def organization_by_slug(self, slug: str) -> Organization:
        organization = self.db.scalar(
            select(Organization).where(
                (Organization.slug == slug.strip().lower()) | (Organization.id == slug)
            )
        )

        if organization is None:
            raise AuthError("not_found", f"no organization {slug.strip()}", 404)

        return organization

    def create_user(
        self,
        name: str,
        email: str,
        password: Optional[str] = None,
        organization: Optional[Organization] = None,
        role: str = "developer",
    ) -> User:
        """A new account; without `password` it gets an unguessable one and is meant to receive a set-password link."""
        email = email.strip().lower()
        name = name.strip()

        if not name or not EMAIL.match(email):
            raise AuthError("invalid", "a name and a valid email are required")

        if role not in ROLES:
            raise AuthError("invalid", f"role must be one of {', '.join(ROLES)}")

        if password is not None and len(password) < PASSWORD_MIN:
            raise AuthError(
                "weak_password", f"password needs at least {PASSWORD_MIN} characters"
            )

        if self.db.scalar(select(User).where(User.email == email)):
            raise AuthError("exists", "an account with this email already exists", 409)

        user = self.new_user(name, email, password or secrets.token_urlsafe(32))

        if organization is not None:
            self.db.add(
                Member(
                    id=new_id(),
                    organization_id=organization.id,
                    user_id=user.id,
                    role=role,
                    created_at=now(),
                )
            )
            self.db.flush()

        return user

    def disable_user(self, user: User) -> int:
        """Turn the account off and end its sessions; its API tokens stop answering until it is enabled again. The count of sessions ended."""
        if user.disabled_at is None:
            user.disabled_at = now()
            user.updated_at = user.disabled_at

        self.db.flush()

        return self.end_sessions(user.id)

    def enable_user(self, user: User) -> None:
        user.disabled_at = None
        user.updated_at = now()
        self.db.flush()
