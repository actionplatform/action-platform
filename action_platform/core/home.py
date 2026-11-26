"""The CLI's config directory: `~/.action-platform`, or `<AP_HOME>/action-platform`, narrowed to `<name>/` by a profile."""

from __future__ import annotations

import os
import re
from pathlib import Path

from action_platform.core.exception import ActionPlatformError

PROFILE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
RESERVED = frozenset({"plugins", "workspaces", "hooks"})


def profile() -> str:
    name = os.environ.get("AP_PROFILE", "").strip()

    if name and (not PROFILE_NAME.match(name) or name in RESERVED):
        raise ActionPlatformError(
            f"invalid profile {name!r}: letters, digits, '-' and '_', not {', '.join(sorted(RESERVED))}"
        )

    return name


def home() -> Path:
    base = os.environ.get("AP_HOME") or os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) / "action-platform" if base else Path.home() / ".action-platform"
    name = profile()

    return root / name if name else root
