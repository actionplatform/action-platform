"""CIRunner ABC."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from action_platform.core.context import Context, RunRef, RunResult


class CIRunner(ABC):
    """CIRunner"""

    name: str

    @abstractmethod
    def trigger(self, ctx: "Context", job: str, params: dict) -> "RunRef":
        """Enqueue pipeline run."""

    @abstractmethod
    def wait(self, ctx: "Context", run: "RunRef", timeout: int = 1800) -> "RunResult":
        """Block until pipeline finishes or timeout."""

    @abstractmethod
    def logs(self, ctx: "Context", run: "RunRef") -> Iterator[str]:
        """Stream pipeline logs."""
