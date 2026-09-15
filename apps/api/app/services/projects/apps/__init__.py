"""Apps: the repositories the platform manages, composed from one module per concern."""

from app.services.projects.apps.service import (
    AppService,
)

__all__ = [
    "AppService",
]
