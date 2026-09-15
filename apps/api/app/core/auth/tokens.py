"""Scoped API tokens: issued, verified, noted, listed, revoked."""

from datetime import timezone
from typing import Optional

from sqlalchemy import select

from app.core.auth import jwt
from app.core.auth.errors import (
    Forbidden,
)
from app.core.db.models import (
    ApiToken,
    ApiTokenClient,
    Session,
)
from action_platform.core.access import (
    Grant,
    grantable_scopes,
)
from app.core.auth.base import (
    ADMIN_TOKEN_TTL,
    AUDIENCE,
    ISSUER,
    TOKEN_TTL,
    AuthBase,
    new_id,
    now,
)


class Tokens(AuthBase):
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
