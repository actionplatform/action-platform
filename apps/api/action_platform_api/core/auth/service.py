import re
import secrets
import string
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from action_platform_api.core.auth import jwt
from action_platform_api.core.auth.errors import (
    AuthError,
    Forbidden,
    Unauthenticated,
)
from action_platform_api.core.auth.passwords import hash_password, verify_password
from action_platform_api.core.auth.secrets import Secrets
from action_platform_api.core.db.models import (
    Account,
    ApiToken,
    ApiTokenClient,
    App,
    DeviceCode,
    Invitation,
    Member,
    Organization,
    OrganizationSetting,
    Project,
    Session,
    User,
)
from action_platform.core.access import (
    DEFAULT_SCOPES,
    ROLES,
    Grant,
    can,
    grantable_scopes,
    normalize_role,
    parse_scopes,
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


class AuthService:
    """Accounts, browser sessions, the device flow and scoped API tokens, on one database session."""

    def __init__(
        self, db: DbSession, secrets: Secrets, verification_uri: str = "/device"
    ) -> None:
        self.db = db
        self.secrets = secrets
        self.verification_uri = verification_uri

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

    def open_session(
        self, user: User, ip: Optional[str] = None, user_agent: Optional[str] = None
    ) -> Session:
        moment = now()
        active = self.db.scalar(
            select(Member.organization_id)
            .where(Member.user_id == user.id)
            .order_by(Member.created_at)
            .limit(1)
        )
        session = Session(
            id=new_id(),
            token=_token(32),
            user_id=user.id,
            expires_at=moment + SESSION_TTL,
            created_at=moment,
            updated_at=moment,
            ip_address=ip,
            user_agent=user_agent,
            active_organization_id=active,
        )
        self.db.add(session)
        self.db.flush()

        return session

    def cookie_for(self, session: Session) -> str:
        return self.secrets.sign_cookie(session.token)

    def session_from_cookie(self, raw: Optional[str]) -> Optional[Session]:
        token = self.secrets.unsign_cookie(raw) if raw else None

        return self.session_from_token(token) if token else None

    def session_from_token(self, token: Optional[str]) -> Optional[Session]:
        if not token:
            return None

        session = self.db.scalar(select(Session).where(Session.token == token))

        if session is None:
            return None

        moment = now()

        if session.expires_at < moment:
            self.db.delete(session)
            self.db.flush()

            return None

        if moment - session.updated_at > SESSION_REFRESH_AFTER:
            session.updated_at = moment
            session.expires_at = moment + SESSION_TTL
            self.db.flush()

        return session

    def require_session(self, token: Optional[str]) -> Session:
        session = self.session_from_token(token)

        if session is None:
            raise Unauthenticated()

        return session

    def sign_out(self, token: str) -> None:
        session = self.db.scalar(select(Session).where(Session.token == token))

        if session:
            self.db.delete(session)
            self.db.flush()

    def sessions_of(self, user_id: str) -> list[Session]:
        rows = self.db.scalars(
            select(Session).where(
                Session.user_id == user_id, Session.expires_at > now()
            )
        ).all()

        return sorted(rows, key=lambda s: s.updated_at, reverse=True)

    def revoke_session(self, user_id: str, id: str) -> bool:
        session = self.db.get(Session, id)

        if session is None or session.user_id != user_id:
            return False

        self.db.delete(session)
        self.db.flush()

        return True

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

    def device_code(self, client_id: Optional[str], scope: Optional[str]) -> DeviceCode:
        moment = now()
        code = DeviceCode(
            id=new_id(),
            device_code=secrets.token_hex(20),
            user_code="".join(secrets.choice(USER_CODE_ALPHABET) for _ in range(8)),
            status="pending",
            expires_at=moment + DEVICE_TTL,
            polling_interval=DEVICE_INTERVAL,
            client_id=(client_id or "")[:120] or None,
            scope=" ".join(parse_scopes(scope) or DEFAULT_SCOPES),
        )
        self.db.add(code)
        self.db.flush()

        return code

    def device_request(self, user_code: str) -> Optional[DeviceCode]:
        return self.db.scalar(
            select(DeviceCode).where(DeviceCode.user_code == user_code.strip().upper())
        )

    def device_status(self, code: DeviceCode) -> str:
        return "expired" if code.expires_at < now() else code.status

    def device_grant(
        self, session: Session, user_code: str, grant: Grant
    ) -> DeviceCode:
        code = self.device_request(user_code)

        if code is None:
            raise AuthError("invalid_code", "invalid code", 404)

        if self.device_status(code) != "pending":
            raise AuthError(
                self.device_status(code), f"this code is {self.device_status(code)}"
            )

        if grant.organization_id:
            role = self.role_in(session.user_id, grant.organization_id)

            if role is None:
                raise Forbidden("you are not a member of that organization")

            allowed = grantable_scopes(role)
        else:
            roles = [
                self.role_in(session.user_id, o.id)
                for o in self.organizations_of(session.user_id)
            ]
            allowed = (
                [
                    s
                    for s in parse_scopes(" ".join(grant.scope))
                    if all(s in grantable_scopes(r) for r in roles)
                ]
                if roles
                else []
            )

        code.scope = self._narrow(grant, allowed).format()
        self.db.flush()

        return code

    def _narrow(self, grant: Grant, allowed: list[str]) -> Grant:
        scope = [s for s in grant.scope if s in allowed]

        if "read" not in scope:
            raise Forbidden("your role does not allow any of the requested scopes")

        if grant.project_id and not self.db.scalar(
            select(Project.id).where(
                Project.id == grant.project_id,
                Project.organization_id == grant.organization_id,
            )
        ):
            raise AuthError("invalid", "that project is not in the organization")

        if grant.app_id and not self.db.scalar(
            select(App.id)
            .join(Project, Project.id == App.project_id)
            .where(App.id == grant.app_id, Project.id == grant.project_id)
        ):
            raise AuthError("invalid", "that app is not in the project")

        return Grant(scope, grant.organization_id, grant.project_id, grant.app_id)

    def device_approve(self, session: Session, user_code: str) -> DeviceCode:
        code = self.device_request(user_code)

        if code is None:
            raise AuthError("invalid_code", "invalid code", 404)

        if self.device_status(code) != "pending":
            raise AuthError(
                self.device_status(code), f"this code is {self.device_status(code)}"
            )

        grant = Grant.parse(code.scope)

        if grant.organization_id is None and not self.organizations_of(session.user_id):
            raise Forbidden("join an organization before approving a device")

        code.status = "approved"
        code.user_id = session.user_id
        self.db.flush()

        return code

    def device_deny(self, session: Session, user_code: str) -> DeviceCode:
        code = self.device_request(user_code)

        if code is None:
            raise AuthError("invalid_code", "invalid code", 404)

        if self.device_status(code) == "pending":
            code.status = "denied"
            code.user_id = session.user_id
            self.db.flush()

        return code

    def device_token(
        self, device_code: str, client_id: Optional[str]
    ) -> tuple[Session, str]:
        code = self.db.scalar(
            select(DeviceCode).where(DeviceCode.device_code == device_code)
        )

        if code is None or (
            code.client_id and client_id and code.client_id != client_id
        ):
            raise AuthError("invalid_grant", "unknown device code")

        moment = now()

        if code.expires_at < moment:
            raise AuthError("expired_token", "the code expired")

        too_fast = bool(code.last_polled_at) and (
            moment - code.last_polled_at
        ).total_seconds() < (
            code.polling_interval
            if code.polling_interval is not None
            else DEVICE_INTERVAL
        )
        code.last_polled_at = moment
        self.db.commit()

        if too_fast:
            raise AuthError("slow_down", "polling too fast")

        if code.status == "pending":
            raise AuthError(
                "authorization_pending", "waiting for approval in the browser"
            )

        if code.status == "denied":
            raise AuthError("access_denied", "login denied in the browser")

        if code.status != "approved" or not code.user_id:
            raise AuthError("invalid_grant", "this code was already used")

        user = self.db.get(User, code.user_id)

        if user is None:
            raise AuthError("invalid_grant", "the account no longer exists")

        code.status = "used"
        session = self.open_session(user, user_agent=code.client_id)

        return session, code.scope or ""

    def issue_token(
        self, session: Session, grant: Grant, name: str
    ) -> tuple[ApiToken, str]:
        name = name.strip()[:120] or "token"

        if grant.organization_id == "*":
            grant = Grant(grant.scope, None, grant.project_id, grant.app_id)
        elif grant.organization_id is None:
            grant = Grant(
                grant.scope,
                session.active_organization_id,
                grant.project_id,
                grant.app_id,
            )

        if grant.organization_id:
            role = self.role_in(session.user_id, grant.organization_id)

            if role is None:
                raise Forbidden("you are not a member of that organization")

            allowed = grantable_scopes(role)
        else:
            organizations = self.organizations_of(session.user_id)

            if not organizations:
                raise Forbidden("join an organization before issuing a token")

            roles = [self.role_in(session.user_id, o.id) for o in organizations]
            allowed = [
                s for s in grant.scope if all(s in grantable_scopes(r) for r in roles)
            ]

        grant = self._narrow(grant, allowed)
        scope = grant.scope
        moment = now()
        token = ApiToken(
            id=new_id(),
            user_id=session.user_id,
            organization_id=grant.organization_id,
            name=name,
            scope=" ".join(scope),
            project_id=grant.project_id,
            app_id=grant.app_id,
            created_at=moment,
            expires_at=moment + (ADMIN_TOKEN_TTL if "admin" in scope else TOKEN_TTL),
        )
        self.db.add(token)
        self.db.flush()
        claims = {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "sub": session.user_id,
            "jti": token.id,
            "iat": int(moment.replace(tzinfo=timezone.utc).timestamp()),
            "exp": int(token.expires_at.replace(tzinfo=timezone.utc).timestamp()),
            "scope": token.scope,
        }

        if grant.organization_id:
            claims["org"] = grant.organization_id

        if grant.project_id:
            claims["project"] = grant.project_id

        if grant.app_id:
            claims["app"] = grant.app_id

        return token, jwt.encode(claims, self.secrets.subkey("api-token"))

    def verify_token(
        self, raw: str, client: Optional[str] = None
    ) -> Optional[ApiToken]:
        claims = jwt.decode(raw, self.secrets.subkey("api-token"), ISSUER, AUDIENCE)

        if not claims or not claims.get("jti") or not claims.get("sub"):
            return None

        token = self.db.get(ApiToken, claims["jti"])

        if (
            token is None
            or token.revoked_at is not None
            or token.user_id != claims["sub"]
        ):
            return None

        if (token.organization_id or None) != (claims.get("org") or None):
            return None

        moment = now()

        if token.expires_at < moment:
            return None

        if (
            token.last_used_at is None
            or (moment - token.last_used_at).total_seconds() > 60
        ):
            token.last_used_at = moment

        if client:
            self.note_client(token, client.strip()[:120])

        self.db.flush()

        return token

    def note_client(self, token: ApiToken, name: str) -> None:
        if not name:
            return

        moment = now()
        seen = self.db.scalar(
            select(ApiTokenClient).where(
                ApiTokenClient.token_id == token.id, ApiTokenClient.name == name
            )
        )

        if seen is None:
            self.db.add(
                ApiTokenClient(
                    id=new_id(),
                    token_id=token.id,
                    name=name,
                    first_seen_at=moment,
                    last_seen_at=moment,
                )
            )
        elif (moment - seen.last_seen_at).total_seconds() > 60:
            seen.last_seen_at = moment

    def tokens_of(
        self, user_id: str, organization_id: Optional[str] = None
    ) -> list[ApiToken]:
        query = select(ApiToken).where(
            ApiToken.user_id == user_id,
            ApiToken.revoked_at.is_(None),
            ApiToken.expires_at > now(),
        )

        if organization_id:
            query = query.where(ApiToken.organization_id == organization_id)

        return sorted(
            self.db.scalars(query).all(), key=lambda t: t.created_at, reverse=True
        )

    def clients_of(self, tokens: list[ApiToken]) -> dict[str, list[ApiTokenClient]]:
        out: dict[str, list[ApiTokenClient]] = {t.id: [] for t in tokens}

        if not tokens:
            return out

        for client in self.db.scalars(
            select(ApiTokenClient).where(ApiTokenClient.token_id.in_(list(out)))
        ):
            out[client.token_id].append(client)

        for clients in out.values():
            clients.sort(key=lambda c: c.last_seen_at, reverse=True)

        return out

    def revoke_token(self, user_id: str, id: str) -> bool:
        token = self.db.get(ApiToken, id)

        if token is None or token.user_id != user_id:
            return False

        token.revoked_at = now()
        self.db.flush()

        return True
