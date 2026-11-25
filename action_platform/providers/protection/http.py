"""One JSON call to a code host for the protection providers, with the HTTP status of a refusal kept."""

from __future__ import annotations

import re
from typing import Any, Callable, Optional

from action_platform.core import destination
from action_platform.core.exception import ProviderError
from action_platform.providers.source import rest

STATUS = re.compile(r"→ (\d{3})(?::\s*(.*))?$", re.S)

Send = Callable[[str, str, Optional[dict]], Any]


class HostRefused(ProviderError):
    def __init__(self, message: str, status: int = 0, detail: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.detail = detail or message


def sender(api: str, headers: dict[str, str]) -> Send:
    """A `send(method, path_or_url, body)` bound to `api`; an absolute URL (a pagination link) must stay on `api`'s origin."""

    def send(method: str, path: str, body: Optional[dict] = None) -> Any:
        url = (
            destination.same_origin(path, api)
            if path.startswith("http")
            else f"{api}{path}"
        )

        try:
            return rest.call(method, url, headers, body)
        except ProviderError as e:
            match = STATUS.search(str(e))

            if match is None:
                raise HostRefused(str(e)) from e

            raise HostRefused(
                str(e), int(match.group(1)), (match.group(2) or "").strip()
            ) from e

    return send
