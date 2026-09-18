"""Action Platform logging module — and the sink a job's output flows through while it runs.

`capture(sink)` routes, for the block, every record of the `action_platform` loggers and every line a plugin `emit`s to `sink`; the hosted worker stores them per job, the CLI leaves the sink unset and the console keeps working."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable, Iterator, Optional

from rich.logging import RichHandler

Sink = Callable[[str], None]

_sink: ContextVar[Optional[Sink]] = ContextVar("action_platform_log_sink", default=None)


class SinkHandler(logging.Handler):
    """Forwards records to the sink of the current context, when there is one."""

    def emit(self, record: logging.LogRecord) -> None:
        sink = _sink.get()

        if sink is None:
            return

        try:
            sink(self.format(record))
        except Exception:
            self.handleError(record)


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=False, show_path=False)],
)

logger = logging.getLogger("action_platform")
logger.setLevel(logging.INFO)

_handler = SinkHandler()
_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_handler)


def emit(line: str) -> None:
    """One line of a running process for whoever follows the job; nothing when nobody does."""
    sink = _sink.get()

    if sink is not None:
        sink(line.rstrip("\n"))


def sink() -> Optional[Sink]:
    return _sink.get()


@contextmanager
def capture(target: Sink) -> Iterator[None]:
    token = _sink.set(target)

    try:
        yield
    finally:
        _sink.reset(token)


def attach(name: str) -> None:
    """Route another logger's records — a plugin's, the API's — through the sink too."""
    other = logging.getLogger(name)

    if other.level == logging.NOTSET or other.level > logging.INFO:
        other.setLevel(logging.INFO)

    if not any(isinstance(h, SinkHandler) for h in other.handlers):
        other.addHandler(_handler)
