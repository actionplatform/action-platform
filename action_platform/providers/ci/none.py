"""No CI: a generic git server, or an app nobody connected to one."""

from __future__ import annotations

from action_platform.abc.ci_runner import CIRunner
from action_platform.core.context import Run


class CINone(CIRunner):
    name = "none"
    embedded = True

    def test(self) -> None:
        return None

    def runs(self, job: str, limit: int = 50) -> list[Run]:
        return []
