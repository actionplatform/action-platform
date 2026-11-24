"""The invitation email: composed from the invitation, sent when a mailer is configured, the outcome kept on the invitation."""

from __future__ import annotations

from html import escape
from typing import Any, Mapping, Optional

from action_platform.core.exception import ProviderError
from app.core.db.models import Invitation, Organization, User
from app.core.shared import people
from app.core.shared.mail import Mail, Mailer, mailer_from_env
from app.services.auth.google import GoogleConfig


def invitation_mail(
    invitation: Invitation,
    organization: Organization,
    inviter: User,
    link: str,
    google: bool,
) -> Mail:
    by = people.label(inviter) or "Someone"
    role = invitation.role or "developer"
    until = f"{invitation.expires_at:%Y-%m-%d} UTC"
    with_google = " You can also accept with your Google account." if google else ""
    text = (
        f"{by} invited you to join {organization.name} on Action Platform as {role}.\n\n"
        f"Accept the invitation before {until}:\n\n"
        f"{link}\n\n"
        f"The invitation is for this email address only.{with_google}"
    )
    html = (
        f"<p>{escape(by)} invited you to join <strong>{escape(organization.name)}</strong> "
        f"on Action Platform as {escape(role)}.</p>"
        f"<p>Accept the invitation before {until}:</p>"
        f'<p><a href="{escape(link)}">Accept the invitation</a></p>'
        f"<p>The invitation is for this email address only.{with_google}</p>"
    )

    return Mail(
        invitation.email or "",
        f"{by} invited you to {organization.name} on Action Platform",
        text,
        html,
    )


class InvitationSender:
    """Without a mailer nothing is sent and the invitation stays a link to share; a failed send never fails the invitation."""

    def __init__(
        self, mailer: Optional[Mailer], public_url: str, google: bool = False
    ) -> None:
        self.mailer = mailer
        self.public_url = public_url.rstrip("/")
        self.google = google

    @classmethod
    def from_env(cls, env: Mapping[str, Any], public_url: str) -> "InvitationSender":
        return cls(
            mailer_from_env(env), public_url, GoogleConfig.from_env(env).configured
        )

    @property
    def enabled(self) -> bool:
        return self.mailer is not None

    def link(self, id: str) -> str:
        return f"{self.public_url}/invite/{id}"

    def send(self, writes: Any, id: str) -> None:
        if self.mailer is None:
            return

        found = writes.invitation(id)

        if found is None or not found[0].email:
            return

        invitation, inviter, organization = found

        try:
            self.mailer.send(
                invitation_mail(
                    invitation,
                    organization,
                    inviter,
                    self.link(invitation.id),
                    self.google,
                )
            )
        except ProviderError as e:
            writes.record_invitation_email(id, str(e))

            return

        writes.record_invitation_email(id, None)


def email_state(invitation: Invitation, enabled: bool) -> str:
    """sent, failed, not_sent (a mailer exists but nothing went out) or off (no mailer, or a login invitation: the link is shared by hand)."""
    if not invitation.email:
        return "off"

    if invitation.email_error:
        return "failed"

    if invitation.emailed_at is not None:
        return "sent"

    return "not_sent" if enabled else "off"
