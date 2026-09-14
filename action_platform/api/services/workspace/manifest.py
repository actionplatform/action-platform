import tomllib
from pathlib import Path

from fastapi import HTTPException

from action_platform.api.services.workspace import ensure_platform, workspace_of
from action_platform.core.flow.repository import Repository
from action_platform.settings import settings

__all__ = ["ensure_platform", "read_manifest", "workspace_of"]


def read_manifest(root: Path) -> dict:
    path = root / settings.CONFIG_FILE

    if not path.exists():
        raise HTTPException(400, f"{settings.CONFIG_FILE} not found in {root}")

    data = tomllib.loads(path.read_text())
    last = root / settings.LAST_VERSION_FILE
    tagged = Repository(root).has_tag("v[0-9]*") if (root / ".git").exists() else True

    return {
        "project": dict(data.get("project", {})),
        "source_host": data.get("source_host", {}),
        "deploy": data.get("deploy", {}),
        "release": data.get("release", {}),
        "services": data.get("services", {}),
        "last_version": (
            (last.read_text().strip() if tagged else "0.0.0") if last.exists() else None
        ),
    }
