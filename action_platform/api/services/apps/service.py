"""Apps: the repositories the platform manages, composed from one module per concern."""

from action_platform.api.services.apps.generate import AppScaffolding
from action_platform.api.services.apps.inventory import AppInventory
from action_platform.api.services.apps.remote import AppRemote


class AppService(AppInventory, AppScaffolding, AppRemote):
    pass


__all__ = ["AppService"]
