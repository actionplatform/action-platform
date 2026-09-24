"""Optional Sentry reporting, shared by the CLI and the API."""

from __future__ import annotations

from typing import Optional

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None

from action_platform import __version__
from action_platform.options import ObservabilityConfig


def observe(
    component: str, config: ObservabilityConfig, version: Optional[str] = None
) -> bool:
    """Start Sentry for `component` with the `config` its entry point read; an empty dsn or a missing SDK leaves it off."""
    if not config.dsn:
        return False

    if sentry_sdk is None:
        return False

    sentry_sdk.init(
        dsn=config.dsn,
        release=f"{component}@{version or __version__}",
        environment=config.environment,
        send_default_pii=False,
        enable_logs=True,
        traces_sample_rate=config.traces_sample_rate,
    )
    sentry_sdk.set_tag("component", component)

    return True
