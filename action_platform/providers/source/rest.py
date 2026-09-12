"""Tiny JSON-over-HTTPS helper shared by the REST source-host providers. Standard library only."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Optional

from action_platform.core.exception import ProviderError


def call(
    method: str,
    url: str,
    headers: dict[str, str],
    body: Optional[dict] = None,
    ok: tuple[int, ...] = (200, 201, 204),
) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "accept": "application/json",
            "user-agent": "action-platform",
            **({"content-type": "application/json"} if data is not None else {}),
            **headers,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            raw = res.read()

            if res.status not in ok:
                raise ProviderError(f"{method} {url} → {res.status}")

            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            payload = json.loads(raw)
            detail = payload.get("message") or payload.get("error") or str(payload)
            errors = payload.get("errors")
            if isinstance(errors, list):
                extra = [
                    x.get("message") if isinstance(x, dict) else str(x) for x in errors
                ]
                detail = f"{detail} ({'; '.join(m for m in extra if m)})"
        except ValueError:
            detail = raw or e.reason

        raise ProviderError(f"{method} {url} → {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise ProviderError(f"cannot reach {url}: {e.reason}") from e
