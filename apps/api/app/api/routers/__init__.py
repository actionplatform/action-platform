"""Every route the API serves: workspace routes under /api (and /api/v1 through the gate), the directory and management routes, auth, imports."""

from app.api.routers.auth import router as auth
from app.api.routers.directory import router as directory
from app.api.routers.imports import router as imports
from app.api.routers.management import router as management
from app.api.routers.workspace import router as workspace

__all__ = ["auth", "directory", "imports", "management", "workspace"]
