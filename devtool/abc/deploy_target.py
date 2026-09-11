"""DeployTarget ABC."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devtool.core.context import Context, DeployResult


class DeployTarget(ABC):
    """DeployTarget"""

    name: str

    @abstractmethod
    def preflight(self, ctx: "Context") -> None:
        """Validate credentials, connectivity, artifacts."""

    @abstractmethod
    def deploy(self, ctx: "Context") -> "DeployResult":
        """Publish artifact or promote application."""

    @abstractmethod
    def rollback(self, ctx: "Context", to_version: str) -> None:
        """Revert to previous version."""
