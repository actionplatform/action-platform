"""CIRunner ABC and the read-only shapes it answers in: a run's stages, a chunk of its log, its tests and artifacts, the queue and the executors."""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Iterable, Iterator, Optional

from action_platform.core.context import Cause, Change

if TYPE_CHECKING:
    from action_platform.core.context import Context, Run, RunRef, RunResult


@dataclass(frozen=True)
class Stage:
    """One stage of a run, or one parallel branch of it (`parent_id` names the stage it runs under)."""

    id: str
    name: str
    status: str
    started_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    parent_id: Optional[str] = None

    def as_tuple(self) -> tuple[str, str]:
        return (self.name, self.status)


@dataclass(frozen=True)
class LogChunk:
    """Log text from offset `start` on: `next_start` is where the next read resumes, `more` whether the run is still writing."""

    text: str
    next_start: int
    more: bool = False


@dataclass(frozen=True)
class TestFailure:
    __test__ = False

    name: str
    class_name: str = ""
    message: str = ""
    stack: str = ""


@dataclass(frozen=True)
class TestReport:
    __test__ = False

    total: int
    failed: int
    skipped: int = 0
    failures: list[TestFailure] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return self.total - self.failed - self.skipped


@dataclass(frozen=True)
class Artifact:
    path: str
    size: Optional[int] = None


@dataclass(frozen=True)
class QueueItem:
    """A run waiting to start: the job, since when and why it waits."""

    job: str
    since: Optional[datetime] = None
    why: Optional[str] = None


@dataclass(frozen=True)
class Executor:
    """A slot a run executes on; `job` and `number` say what it runs while `busy`."""

    node: str
    busy: bool
    job: Optional[str] = None
    number: Optional[int] = None


@dataclass(frozen=True)
class PendingInput:
    """A run paused on a question to a person."""

    id: str
    message: str


def stage_tuples(stages: Iterable[Stage | tuple[str, str]]) -> list[tuple[str, str]]:
    """`(name, status)` for each stage, whether the runner answered `Stage`s or the earlier tuples."""
    return [s.as_tuple() if isinstance(s, Stage) else (s[0], s[1]) for s in stages]


class CIRunner(ABC):
    """A CI system: what it ran for a job, and — where the provider supports it — starting a run, waiting for it and reading its logs, stages, tests, artifacts, queue and executors.

    `embedded` runners live inside the source host (GitHub Actions, GitLab CI) and authenticate with its token; the others are servers of their own, brought by a plugin, with their own credentials. Every read raises NotImplementedError when the CI cannot answer it.
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
        """One run of `job`, with its parameters, causes and changes where the CI records them."""
        raise NotImplementedError(f"{self.name} cannot read a run")

    def trigger(self, ctx: "Context", job: str, params: dict) -> "RunRef":
        """Enqueue pipeline run."""
        raise NotImplementedError(f"{self.name} cannot trigger runs")

    def start(self, job: str, ref: str, params: dict | None = None) -> "RunRef":
        """Start a run of `job` on `ref` (a branch or tag) from outside a release — what Run CI on an app's Overview does."""
        raise NotImplementedError(f"{self.name} cannot start runs")

    def run_of(self, job: str, ref: "RunRef") -> "Run | None":
        """The run a `start` became, once the server has given it a number; None while it waits. NotImplementedError when the server cannot tell, and the run is looked for among the job's runs."""
        raise NotImplementedError(f"{self.name} cannot follow a started run")

    def stages(self, job: str, number: int) -> list[Stage]:
        """The stages of one run, parallel branches included, in order; `stage_tuples` gives the earlier `(name, status)` form."""
        raise NotImplementedError(f"{self.name} cannot read stages")

    def wait(self, ctx: "Context", run: "RunRef", timeout: int = 1800) -> "RunResult":
        """Block until pipeline finishes or timeout."""
        raise NotImplementedError(f"{self.name} cannot wait for runs")

    def logs(self, ctx: "Context", run: "RunRef") -> Iterator[str]:
        """Stream pipeline logs."""
        raise NotImplementedError(f"{self.name} cannot read logs")

    def log(
        self, job: str, number: int, start: int = 0, node: str | None = None
    ) -> LogChunk:
        """The log of one run from offset `start` — the whole console, or one stage or step when `node` names it; read again from `next_start` while `more`."""
        raise NotImplementedError(f"{self.name} cannot read a log")

    def tests(self, job: str, number: int) -> TestReport | None:
        """The test report of one run; None when it published none."""
        raise NotImplementedError(f"{self.name} cannot read test reports")

    def artifacts(self, job: str, number: int) -> list[Artifact]:
        """The files one run archived."""
        raise NotImplementedError(f"{self.name} cannot list artifacts")

    def artifact(self, job: str, number: int, path: str) -> Iterator[bytes]:
        """The content of one archived file, in chunks."""
        raise NotImplementedError(f"{self.name} cannot read artifacts")

    def queue(self) -> list[QueueItem]:
        """The runs waiting to start."""
        raise NotImplementedError(f"{self.name} cannot read its queue")

    def executors(self) -> list[Executor]:
        """The slots runs execute on and what each runs."""
        raise NotImplementedError(f"{self.name} cannot list executors")

    def pending_inputs(self, job: str, number: int) -> list[PendingInput]:
        """The questions one run waits on."""
        raise NotImplementedError(f"{self.name} cannot read pending inputs")


__all__ = [
    "Artifact",
    "CIRunner",
    "Cause",
    "Change",
    "Executor",
    "LogChunk",
    "PendingInput",
    "QueueItem",
    "Stage",
    "TestFailure",
    "TestReport",
    "stage_tuples",
]
