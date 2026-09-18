"""DeployTarget ABC — the lifecycle every deploy target answers to.

Vocabulary mirrors what a deployment scope needs over its life: provision the
target once, ship versions, move traffic, undo, inspect, tear down, and — for
every target, whoever executed the deploy — verify that a version is there. A
target that cannot do one of them raises NotImplementedError and the CLI says so.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from action_platform.core.context import Context, DeployResult, Diagnosis


class DeployTarget(ABC):
    """DeployTarget"""

    name: str

    @abstractmethod
    def preflight(self, ctx: "Context") -> None:
        """Validate credentials, tooling, artifacts. Raise DeployError otherwise."""

    def create(self, ctx: "Context") -> None:
        """Provision the target itself (stack, app, registry). Idempotent."""
        raise NotImplementedError(f"{self.name} cannot create")

    @abstractmethod
    def deploy(self, ctx: "Context") -> "DeployResult":
        """Ship the current version."""

    def switch_traffic(self, ctx: "Context", weight: int) -> None:
        """Move `weight` percent of traffic to the newest version (blue-green)."""
        raise NotImplementedError(f"{self.name} cannot switch traffic")

    def rollback(self, ctx: "Context", to_version: str | None = None) -> None:
        """Revert to `to_version` or the previous one."""
        raise NotImplementedError(f"{self.name} cannot rollback")

    def diagnose(self, ctx: "Context") -> "Diagnosis":
        """Health, last deploy, logs pointer."""
        raise NotImplementedError(f"{self.name} cannot diagnose")

    def delete(self, ctx: "Context") -> None:
        """Tear the target down."""
        raise NotImplementedError(f"{self.name} cannot delete")

    def verify(self, version: str, stage: str | None = None) -> bool:
        """Whether `version` is really at the destination — asked after any executor reported success."""
        raise NotImplementedError(f"{self.name} cannot verify")

    def url(self, version: str, stage: str | None = None) -> str | None:
        """Where `version` can be seen at the destination, when the target knows."""
        return None
