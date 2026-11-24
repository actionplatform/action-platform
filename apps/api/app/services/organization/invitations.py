"""Accepting an invitation bound to a code-host login: the person proves the login through the host's OAuth app, then joins."""

from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.orm import Session as DbSession

from action_platform.core.exception import ActionPlatformError
from app.core.auth.crypto import Sealer
from app.core.auth.secrets import Secrets
from app.core.db.models import Invitation, Organization, User
from app.core.errors import Forbidden, Invalid, NotFound, Upstream
from app.repositories.organization import OrganizationRepository
from app.services.integrations.hosts.directory import IntegrationsDirectory
from app.services.integrations.hosts.registry import HostProviders
from app.services.integrations.hosts.state import OAuthState

STATE_PREFIX = "invite."
IDENTITY_SCOPES = {"github": "", "gitlab": "read_user"}


class InvitationProof:
    def __init__(
        self,
        db: DbSession,
        sealer: Optional[Sealer],
        secrets: Secrets,
        providers: HostProviders,
    ) -> None:
        self.directory = OrganizationRepository(db, sealer)
        self.integrations = IntegrationsDirectory(db, sealer, providers)
        self.providers = providers
        self.signer = OAuthState(secrets)

    def start(self, id: str, user: User, origin: str) -> str:
        """Where the browser goes to sign in to the code host as the invited login."""
        invitation = self._pending_login_invitation(id)
        provider = self.providers.get(invitation.host_kind or "")
        app = self.integrations.oauth_app(provider.kind)

        if app is None:
            raise Invalid(
                f"{provider.label} sign-in is not configured on this platform: "
                "ask an admin to invite you by email"
            )

        state = f"{STATE_PREFIX}{invitation.id}." + self.signer.sign(
            f"invitation:{invitation.id}", f"/invite/{invitation.id}", user.id
        )

        return self._identity_only(
            provider.kind, provider.authorize_url(app, origin, state)
        )

    def finish(
        self, id: str, user: User, origin: str, code: str, state: str
    ) -> Organization:
        """Trade the code for the login it belongs to and accept the invitation when it is the invited one."""
        prefix = f"{STATE_PREFIX}{id}."
        signed = self.signer.verify(state.removeprefix(prefix), user.id)

        if (
            not state.startswith(prefix)
            or signed is None
            or signed.get("orgId") != f"invitation:{id}"
        ):
            raise Forbidden("invalid or expired state")

        invitation = self._pending_login_invitation(id)
        provider = self.providers.get(invitation.host_kind or "")
        app = self.integrations.oauth_app(provider.kind)

        if app is None:
            raise Invalid(f"{provider.label} sign-in is not configured")

        try:
            token, _, _ = provider.exchange_code(app, origin, code)
            login, _ = provider.identity(app, token)
        except ActionPlatformError as e:
            raise Upstream(str(e)) from e

        return self.directory.accept_invitation(id, user, verified_login=login)

    def _pending_login_invitation(self, id: str) -> Invitation:
        found = self.directory.invitation(id)

        if found is None:
            raise NotFound("invitation not found")

        invitation = found[0]

        if not invitation.host_login:
            raise Invalid("this invitation is accepted by email, not by login")

        if invitation.status != "pending":
            raise Invalid(f"invitation {invitation.status}")

        return invitation

    @staticmethod
    def _identity_only(kind: str, url: str) -> str:
        if kind not in IDENTITY_SCOPES:
            return url

        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query["scope"] = IDENTITY_SCOPES[kind]

        return urlunsplit(parts._replace(query=urlencode(query)))
