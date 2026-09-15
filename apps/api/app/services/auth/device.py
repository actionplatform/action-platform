"""The device flow (RFC 8628): a code for the CLI or MCP, approved in the browser."""

import secrets
from typing import Optional

from sqlalchemy import select

from action_platform.core.access import (
    DEFAULT_SCOPES,
    Grant,
    grantable_scopes,
    parse_scopes,
)
from app.services.auth.base import (
    DEVICE_INTERVAL,
    DEVICE_TTL,
    USER_CODE_ALPHABET,
    AuthBase,
    new_id,
    now,
)
from app.services.auth.errors import (
    AuthError,
    Forbidden,
)
from app.core.db.models import (
    App,
    DeviceCode,
    Project,
    Session,
    User,
)


class Device(AuthBase):
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
