"""Tiny JSON-over-HTTPS helper shared by the REST source-host providers. Standard library only."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
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


def get_pages(url: str, headers: dict[str, str], limit: int = 20) -> list[Any]:
    """Every row of a `per_page`/`page` paginated listing (GitHub, GitLab), up to `limit` pages."""
    out: list[Any] = []
    separator = "&" if "?" in url else "?"

    for page in range(1, limit + 1):
        rows = call("GET", f"{url}{separator}per_page=100&page={page}", headers)

        if not isinstance(rows, list):
            break

        out.extend(rows)

        if len(rows) < 100:
            break

    return out


def get_values(url: str, headers: dict[str, str]) -> list[Any]:
    """Every row of a `values`/`next` paginated listing (Bitbucket)."""
    out: list[Any] = []
    next_url: Optional[str] = url

    while next_url:
        data = call("GET", next_url, headers) or {}
        out.extend(data.get("values", []))
        next_url = data.get("next")

    return out


def parse_utc(value: Optional[str]) -> Optional[datetime]:
    """An ISO timestamp from a provider, as naive UTC."""
    if not value:
        return None

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    return (
        parsed.astimezone(timezone.utc).replace(tzinfo=None)
        if parsed.tzinfo
        else parsed
    )
