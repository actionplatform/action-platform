"""Tools that act on a hosted platform through `action-platform login`, not on the local checkout — one module per concern."""

from __future__ import annotations

from typing import Any

from action_platform.mcp.tools.remote import (
    access,
    adoption,
    apps,
    ci,
    configuration,
    context,
    deploy,
    directory,
    flow,
    github,
    jobs,
    matrix,
    protection,
)
from action_platform.remote.client import Remote

MODULES = (
    directory,
    context,
    apps,
    flow,
    configuration,
    deploy,
    jobs,
    ci,
    protection,
    adoption,
    matrix,
    access,
    github,
)


def register(mcp: Any, remote: Remote) -> None:
    for module in MODULES:
        module.register(mcp, remote)
