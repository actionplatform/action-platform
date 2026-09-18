"""Action Platform __init__ module."""

__version__ = "0.23.0"
__description__ = "Your platform team, as a CLI."

from .core import extensions
from .core.config import Config
from .core.context import Context
from .core.action_platform import ActionPlatform
from .plugins import registry

extensions.provide(registry.installed)

__all__ = ["Config", "Context", "ActionPlatform"]
