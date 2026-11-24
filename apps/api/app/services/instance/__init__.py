"""The instance as an operator sees it: is it healthy, and can it send email."""

from app.services.instance.health import InstanceHealth
from app.services.instance.mail import MailLog, probe_mail

__all__ = ["InstanceHealth", "MailLog", "probe_mail"]
