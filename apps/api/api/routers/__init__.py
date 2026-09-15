"""Every route the API serves: workspace routes under /api (and /api/v1 through the gate), the directory and management routes, auth, imports."""

from action_platform_api.api.routers.auth import router as auth
from action_platform_api.api.routers.directory import router as directory
from action_platform_api.api.routers.imports import router as imports
from action_platform_api.api.routers.management import router as management
from action_platform_api.api.routers.workspace import router as workspace

__all__ = ["auth", "directory", "imports", "management", "workspace"]
