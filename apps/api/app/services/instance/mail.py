"""What the instance last failed to email, and the message an owner sends to see email work."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from html import escape
from typing import Optional

from app.core.db.models import User
from app.core.shared.clock import now
from app.core.shared.mail import Mail


@dataclass(frozen=True)
class MailFailure:
    at: datetime
    what: str
    error: str


class MailLog:
    """The last email this API process could not send; a send that works clears it."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.last: Optional[MailFailure] = None

    def failed(self, what: str, error: str) -> None:
        with self.lock:
            self.last = MailFailure(now(), what, error)

    def sent(self) -> None:
        with self.lock:
            self.last = None


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
