"""Apps: the repositories the platform manages, composed from one module per concern."""

from app.services.apps.generate import AppScaffolding
from app.services.apps.inventory import AppInventory
from app.services.apps.remote import AppRemote


class AppService(AppInventory, AppScaffolding, AppRemote):
    pass


__all__ = ["AppService"]
