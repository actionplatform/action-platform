"""Where `action-platform login` keeps the token: ~/.action-platform/credentials.json, mode 600."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


def path() -> Path:
    base = os.environ.get("AP_HOME") or os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) / "action-platform" if base else Path.home() / ".action-platform"

    return root / "credentials.json"


@dataclass
class Credentials:
    server: str
    token: str
    scope: str = ""


def load() -> Optional[Credentials]:
    env_server, env_token = os.environ.get("AP_SERVER"), os.environ.get("AP_TOKEN")

    if env_server and env_token:
        return Credentials(env_server, env_token, os.environ.get("AP_SCOPE", ""))

    file = path()

    if not file.exists():
        return None

    data = json.loads(file.read_text() or "{}")

    if not data.get("server") or not data.get("token"):
        return None

    return Credentials(data["server"], data["token"], data.get("scope", ""))


def save(creds: Credentials) -> None:
    file = path()
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(asdict(creds), indent=2) + "\n")
    file.chmod(0o600)


def clear() -> bool:
    file = path()

    if file.exists():
        file.unlink()
        return True

    return False
