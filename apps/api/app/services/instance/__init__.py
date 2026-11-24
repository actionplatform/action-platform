"""Instance health and the test email."""

from app.services.instance.health import InstanceHealth
from app.services.instance.mail import probe_mail

__all__ = ["InstanceHealth", "probe_mail"]
