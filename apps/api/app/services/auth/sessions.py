"""Browser sessions: opened on sign in, read from a cookie or a bearer, listed and revoked."""

from typing import Optional

from sqlalchemy import delete, select

from app.services.auth.base import (
    SESSION_REFRESH_AFTER,
    SESSION_TTL,
    AuthBase,
    _token,
    new_id,
    now,
)
from app.services.auth.errors import (
    AuthError,
    Unauthenticated,
)
from app.core.db.models import (
    Member,
    Session,
    User,
)


class Sessions(AuthBase):
    def open_session(
        self, user: User, ip: Optional[str] = None, user_agent: Optional[str] = None
    ) -> Session:
        if user.disabled_at is not None:
            raise AuthError("disabled", "this account is disabled", 403)

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
        user = self.db.get(User, session.user_id)

        if session.expires_at < moment or user is None or user.disabled_at is not None:
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

    def end_sessions(self, user_id: str, keep: Optional[str] = None) -> int:
        """Delete every session of the user but `keep`; the count of the ones that were live."""
        query = delete(Session).where(Session.user_id == user_id)

        if keep:
            query = query.where(Session.id != keep)

        live = sum(1 for s in self.sessions_of(user_id) if s.id != keep)
        self.db.execute(query)
        self.db.flush()

        return live
