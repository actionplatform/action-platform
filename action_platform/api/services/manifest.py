import tomllib
from pathlib import Path

from fastapi import HTTPException

from action_platform.api.services.workspace import ensure_platform, workspace_of
from action_platform.settings import settings

__all__ = ["ensure_platform", "read_manifest", "workspace_of"]


def read_manifest(root: Path) -> dict:
    path = root / settings.CONFIG_FILE

    if not path.exists():
        raise HTTPException(400, f"{settings.CONFIG_FILE} not found in {root}")

    data = tomllib.loads(path.read_text())
    last = root / settings.LAST_VERSION_FILE

    return {
        "project": dict(data.get("project", {})),
        "source_host": data.get("source_host", {}),
        "deploy": data.get("deploy", {}),
        "release": data.get("release", {}),
        "services": data.get("services", {}),
        "last_version": last.read_text().strip() if last.exists() else None,
    }
