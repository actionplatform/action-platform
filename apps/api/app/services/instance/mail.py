"""The message an owner sends to see email work."""

from __future__ import annotations

from html import escape

from app.core.db.models import User
from app.core.shared.mail import Mail


def probe_mail(user: User) -> Mail:
    text = (
        f"Hi {user.name},\n\n"
        "This is a test message from your Action Platform instance. "
        "Email works: invitations and password resets reach people the same way."
    )
    html = (
        f"<p>Hi {escape(user.name)},</p>"
        "<p>This is a test message from your Action Platform instance. "
        "Email works: invitations and password resets reach people the same way.</p>"
    )

    return Mail(user.email, "Action Platform test email", text, html)
