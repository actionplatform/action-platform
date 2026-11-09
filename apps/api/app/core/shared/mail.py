"""Outbound email over SMTP, configured by `AP_SMTP_*`; no host set means the API sends no email."""

from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import make_msgid
from typing import Optional, Protocol

from action_platform.core.exception import ConfigError, ProviderError
from action_platform.options import Env, secret

SECURITY = ("starttls", "ssl", "none")
TIMEOUT = 15


@dataclass(frozen=True)
class Mail:
    to: str
    subject: str
    text: str
    html: Optional[str] = None


class Mailer(Protocol):
    def send(self, mail: Mail) -> None: ...


@dataclass(frozen=True)
class SmtpConfig:
    """`AP_SMTP_HOST`, `AP_SMTP_PORT`, `AP_SMTP_USER`, `AP_SMTP_PASSWORD` (or `_FILE`), `AP_SMTP_FROM` and `AP_SMTP_SECURITY` (starttls, ssl or none)."""

    host: str = ""
    port: int = 587
    user: str = ""
    password: str = ""
    sender: str = ""
    security: str = "starttls"

    @classmethod
    def from_env(cls, env: Env) -> "SmtpConfig":
        security = (env.get("AP_SMTP_SECURITY") or cls.security).lower()

        if security not in SECURITY:
            raise ConfigError(
                f"AP_SMTP_SECURITY {security!r} is not one of {', '.join(SECURITY)}"
            )

        default_port = 465 if security == "ssl" else cls.port

        return cls(
            host=env.get("AP_SMTP_HOST", ""),
            port=int(env.get("AP_SMTP_PORT") or default_port),
            user=env.get("AP_SMTP_USER", ""),
            password=secret("AP_SMTP_PASSWORD", env=env),
            sender=env.get("AP_SMTP_FROM", ""),
            security=security,
        )

    @property
    def configured(self) -> bool:
        return bool(self.host)


class SmtpMailer:
    """
    Import:
        from app.core.shared.mail import Mail, SmtpConfig, SmtpMailer

    Example:
        SmtpMailer(SmtpConfig.from_env(os.environ)).send(Mail("ana@example.com", "Hi", "Hello"))

    One connection per message: recovery mail is rare, a pool would hold a
    socket the server closes anyway.
    """

    def __init__(self, config: SmtpConfig) -> None:
        if not config.host:
            raise ConfigError("AP_SMTP_HOST is empty: the API cannot send email")

        if not config.sender:
            raise ConfigError("AP_SMTP_FROM is empty: email needs a sender address")

        self.config = config

    def send(self, mail: Mail) -> None:
        message = self._message(mail)

        try:
            with self._connect() as smtp:
                if self.config.user:
                    smtp.login(self.config.user, self.config.password)

                smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as e:
            raise ProviderError(
                f"cannot send email through {self.config.host}: {e}"
            ) from e

    def _connect(self) -> smtplib.SMTP:
        config = self.config

        if config.security == "ssl":
            return smtplib.SMTP_SSL(
                config.host,
                config.port,
                timeout=TIMEOUT,
                context=ssl.create_default_context(),
            )

        smtp = smtplib.SMTP(config.host, config.port, timeout=TIMEOUT)

        if config.security == "starttls":
            smtp.starttls(context=ssl.create_default_context())

        return smtp

    def _message(self, mail: Mail) -> EmailMessage:
        message = EmailMessage()
        message["From"] = self.config.sender
        message["To"] = mail.to
        message["Subject"] = mail.subject
        message["Message-ID"] = make_msgid()
        message.set_content(mail.text)

        if mail.html:
            message.add_alternative(mail.html, subtype="html")

        return message


def mailer_from_env(env: Env) -> Optional[Mailer]:
    """The mailer `AP_SMTP_*` describe, or None when `AP_SMTP_HOST` is not set."""
    config = SmtpConfig.from_env(env)

    return SmtpMailer(config) if config.configured else None
