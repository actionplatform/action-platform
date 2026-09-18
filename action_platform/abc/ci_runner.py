"""CIRunner ABC."""

from abc import ABC
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from action_platform.core.context import Context, Run, RunRef, RunResult


class CIRunner(ABC):
    """A CI system: what it ran for a job, and — where the provider supports it — starting a run, waiting for it and reading its logs.

    `embedded` runners live inside the source host (GitHub Actions, GitLab CI) and authenticate with its token; the others (Jenkins) are servers of their own with their own credentials.
    """

    name: str
    embedded: bool = False

    def test(self) -> None:
        """Reach the server with the credentials; raise ProviderError when it refuses."""
        raise NotImplementedError(f"{self.name} cannot be tested")

    def runs(self, job: str, limit: int = 50) -> "list[Run]":
        """The latest runs of `job`, newest first."""
        raise NotImplementedError(f"{self.name} cannot list runs")

    def run(self, job: str, number: int) -> "Run":
        """One run of `job`."""
        raise NotImplementedError(f"{self.name} cannot read a run")

    def trigger(self, ctx: "Context", job: str, params: dict) -> "RunRef":
        """Enqueue pipeline run."""
        raise NotImplementedError(f"{self.name} cannot trigger runs")

    def start(self, job: str, ref: str, params: dict | None = None) -> "RunRef":
        """Start a run of `job` on `ref` (a branch or tag) from outside a release — what the CI tab's Run button does."""
        raise NotImplementedError(f"{self.name} cannot start runs")

    def wait(self, ctx: "Context", run: "RunRef", timeout: int = 1800) -> "RunResult":
        """Block until pipeline finishes or timeout."""
        raise NotImplementedError(f"{self.name} cannot wait for runs")

    def logs(self, ctx: "Context", run: "RunRef") -> Iterator[str]:
        """Stream pipeline logs."""
        raise NotImplementedError(f"{self.name} cannot read logs")
