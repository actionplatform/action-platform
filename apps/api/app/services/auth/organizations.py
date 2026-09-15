"""The organizations a user belongs to and the one the session is on."""

from typing import Optional

from sqlalchemy import select

from action_platform.core.access import (
    ROLES,
    can,
    normalize_role,
)
from app.services.auth.base import (
    EMAIL,
    PASSWORD_MIN,
    PROVIDER,
    AuthBase,
    Identity,
    new_id,
    now,
)
from app.services.auth.errors import (
    AuthError,
    Forbidden,
    Unauthenticated,
)
from app.core.auth.passwords import hash_password
from app.core.db.models import (
    Account,
    Member,
    Organization,
    OrganizationSetting,
    Session,
    User,
)


class Organizations(AuthBase):
    def organizations_of(self, user_id: str) -> list[Organization]:
        rows = self.db.execute(
            select(Organization)
            .join(Member, Member.organization_id == Organization.id)
            .where(Member.user_id == user_id)
            .order_by(Organization.name)
        ).scalars()

        return list(rows)

    def role_in(self, user_id: str, organization_id: Optional[str]) -> Optional[str]:
        if not organization_id:
            return None

        return normalize_role(
            self.db.scalar(
                select(Member.role).where(
                    Member.user_id == user_id, Member.organization_id == organization_id
                )
            )
        )

    def identity_of(self, session: Session) -> Identity:
        user = self.db.get(User, session.user_id)

        if user is None:
            raise Unauthenticated()

        organizations = self.organizations_of(user.id)
        organization = next(
            (o for o in organizations if o.id == session.active_organization_id), None
        )

        if organization is None and organizations:
            organization = organizations[0]
            session.active_organization_id = organization.id
            self.db.flush()

        return Identity(
            user,
            session,
            organization,
            self.role_in(user.id, organization.id) if organization else None,
        )

    def set_active_organization(
        self, session: Session, organization_id: str
    ) -> Organization:
        organization = self.db.get(Organization, organization_id)

        if (
            organization is None
            or self.role_in(session.user_id, organization_id) is None
        ):
            raise Forbidden("you are not a member of this organization")

        session.active_organization_id = organization_id
        self.db.flush()

        return organization

    def create_organization(
        self,
        session: Session,
        name: str,
        slug: str,
        git_author_name: Optional[str] = None,
        git_author_email: Optional[str] = None,
    ) -> Organization:
        name = name.strip()
        slug = slug.strip().lower()

        if not name or not slug:
            raise AuthError("invalid", "name and slug are required")

        if self.db.scalar(select(Organization).where(Organization.slug == slug)):
            raise AuthError(
                "exists", "an organization with this slug already exists", 409
            )

        moment = now()
        organization = Organization(
            id=new_id(), name=name, slug=slug, created_at=moment
        )
        self.db.add(organization)
        self.db.add(
            Member(
                id=new_id(),
                organization_id=organization.id,
                user_id=session.user_id,
                role="owner",
                created_at=moment,
            )
        )

        if git_author_name and git_author_email:
            self.db.add(
                OrganizationSetting(
                    organization_id=organization.id,
                    git_author_name=git_author_name,
                    git_author_email=git_author_email,
                    updated_at=moment,
                )
            )

        session.active_organization_id = organization.id
        self.db.flush()

        return organization

    def add_member_account(
        self,
        session: Session,
        organization_id: str,
        name: str,
        email: str,
        password: str,
        role: str,
    ) -> tuple[User, bool]:
        if not can(self.role_in(session.user_id, organization_id), "org.manage"):
            raise Forbidden("only owners and admins can add members")

        if role not in ROLES:
            raise AuthError("invalid", f"role must be one of {', '.join(ROLES)}")

        email = email.strip().lower()
        name = name.strip()

        if not EMAIL.match(email):
            raise AuthError("invalid", "enter a valid email")

        moment = now()
        user = self.db.scalar(select(User).where(User.email == email))
        existed = user is not None

        if user is None:
            if not name:
                raise AuthError("invalid", "name is required")

            if len(password) < PASSWORD_MIN:
                raise AuthError(
                    "weak_password",
                    f"password needs at least {PASSWORD_MIN} characters",
                )

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

        if self.role_in(user.id, organization_id) is not None:
            raise AuthError("exists", "already a member", 409)

        self.db.add(
            Member(
                id=new_id(),
                organization_id=organization_id,
                user_id=user.id,
                role=role,
                created_at=moment,
            )
        )
        self.db.flush()

        return user, existed
