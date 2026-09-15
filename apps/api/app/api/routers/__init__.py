"""Every route the API serves."""

from app.api.routers.auth import router as auth
from app.api.routers.management import router as management
from app.api.routers.workspace import router as workspace

__all__ = ["auth", "management", "workspace"]
