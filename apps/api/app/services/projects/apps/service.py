"""Apps: the repositories the platform manages, composed from one module per concern."""

from app.services.projects.apps.generate import AppScaffolding
from app.services.projects.apps.inventory import AppInventory
from app.services.projects.apps.remote import AppRemote


class AppService(AppInventory, AppScaffolding, AppRemote):
    pass


__all__ = ["AppService"]
