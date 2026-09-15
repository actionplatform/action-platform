"""Optional Sentry reporting, shared by the CLI and the API."""

from __future__ import annotations

from typing import Optional

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None

from action_platform import __version__
from action_platform.settings import settings


def observe(
    component: str, dsn: Optional[str] = None, version: Optional[str] = None
) -> bool:
    dsn = settings.SENTRY_DSN if dsn is None else dsn

    if not dsn:
        return False

    if sentry_sdk is None:
        return False

    sentry_sdk.init(
        dsn=dsn,
        release=f"{component}@{version or __version__}",
        environment=settings.SENTRY_ENVIRONMENT,
        send_default_pii=False,
        enable_logs=True,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
    )
    sentry_sdk.set_tag("component", component)

    return True
