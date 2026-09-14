import tomllib
from pathlib import Path

from fastapi import HTTPException

from action_platform.api.repositories.registry import Entry, Registry
from action_platform.core.exception import ActionPlatformError
from action_platform.core.scaffold.install import InstallError, install
from action_platform.settings import settings


def workspace_of(registry: Registry, id: str) -> tuple[Entry, Path]:
    """The app's clone, with the platform files in place: a clone that lost `platform.toml` (an import whose install was discarded, a branch from before the platform) gets them back on the spot, uncommitted, so the app never shows an error for something the platform can fix itself."""
    entry = registry.get(id)
    root = Path(entry.path)

    if not root.is_dir():
        try:
            registry.restore(entry)
        except ActionPlatformError as e:
            raise HTTPException(
                410,
                f"workspace for {entry.name} is missing here and could not be cloned: {e}",
            ) from e

    if not root.is_dir():
        raise HTTPException(410, f"{root} no longer exists")

    ensure_platform(entry, root)

    return entry, root


def ensure_platform(entry: Entry, root: Path) -> list[str]:
    if (root / settings.CONFIG_FILE).exists() or not (root / ".git").exists():
        return []

    ci = (
        "gitlab"
        if "gitlab" in entry.url
        else "bitbucket"
        if "bitbucket" in entry.url
        else "github"
    )

    try:
        plan = install(root, type_="web", ci=ci, name=entry.name)
    except InstallError:
        plan = install(root, type_="web", language="none", ci=ci, name=entry.name)

    return plan.created


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
