import tomllib
from pathlib import Path

from action_platform.settings import settings


def read_manifest(root: Path) -> dict:
    data = tomllib.loads((root / settings.CONFIG_FILE).read_text())
    last = root / settings.LAST_VERSION_FILE

    return {
        "project": dict(data.get("project", {})),
        "source_host": data.get("source_host", {}),
        "deploy": data.get("deploy", {}),
        "release": data.get("release", {}),
        "services": data.get("services", {}),
        "last_version": last.read_text().strip() if last.exists() else None,
    }
