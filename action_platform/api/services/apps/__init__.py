"""Apps: the repositories the platform manages, composed from one module per concern."""

from action_platform.api.services.apps.generate import Generate
from action_platform.api.services.apps.inventory import Inventory
from action_platform.api.services.apps.remote import Remote


class AppService(Inventory, Generate, Remote):
    pass


__all__ = ["AppService"]
