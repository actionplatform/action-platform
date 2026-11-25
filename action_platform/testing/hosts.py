"""A code host's REST API in memory for the protection providers' tests: answers by (method, path), records every call."""

from __future__ import annotations

import copy
from typing import Any, Callable, Optional, Union

from action_platform.providers.protection.http import HostRefused

Answer = Union[Any, HostRefused, Callable[[Optional[dict]], Any]]


class FakeHost:
    def __init__(self, routes: Optional[dict[tuple[str, str], Answer]] = None) -> None:
        self.routes: dict[tuple[str, str], Answer] = dict(routes or {})
        self.calls: list[tuple[str, str, Optional[dict]]] = []

    def __call__(self, method: str, path: str, body: Optional[dict] = None) -> Any:
        self.calls.append((method, path, copy.deepcopy(body)))
        answer = self.routes.get(
            (method, path),
            HostRefused(f"{method} {path} → 404: Not Found", 404, "Not Found"),
        )

        if isinstance(answer, HostRefused):
            raise answer

        if callable(answer):
            return answer(body)

        return copy.deepcopy(answer)

    def sent(self, method: str) -> list[tuple[str, Optional[dict]]]:
        return [(p, b) for m, p, b in self.calls if m == method]


def refused(status: int, detail: str = "refused") -> HostRefused:
    return HostRefused(f"→ {status}: {detail}", status, detail)
