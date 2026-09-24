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
    dsn = settings.observability.dsn if dsn is None else dsn

    if not dsn:
        return False

    if sentry_sdk is None:
        return False

    sentry_sdk.init(
        dsn=dsn,
        release=f"{component}@{version or __version__}",
        environment=settings.observability.environment,
        send_default_pii=False,
        enable_logs=True,
        traces_sample_rate=settings.observability.traces_sample_rate,
    )
    sentry_sdk.set_tag("component", component)

    return True
