"""A small JSON client over urllib: one per service, credentials in headers that never reach an error message."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional


from action_platform.core.service_access.provider import AccessError

LINK = re.compile(r'<([^>]+)>;\s*rel="next"(?:;\s*results="(true|false)")?')


@dataclass
class Response:
    status: int
    data: Any
    headers: dict[str, str] = field(default_factory=dict)


class Http:
    def __init__(
        self, service: str, base: str, headers: dict[str, str], timeout: float = 30
    ) -> None:
        self.service = service
        self.base = base.rstrip("/")
        self.headers = headers
        self.timeout = timeout

    def url(self, path: str, query: Optional[dict[str, Any]] = None) -> str:
        url = path if path.startswith("http") else f"{self.base}/{path.lstrip('/')}"
        q = {k: v for k, v in (query or {}).items() if v is not None}

        if q:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(q)

        return url

    def send(
        self,
        method: str,
        path: str,
        body: Any = None,
        query: Optional[dict[str, Any]] = None,
        form: Optional[dict[str, Any]] = None,
    ) -> Response:
        headers = {
            "accept": "application/json",
            "user-agent": f"action-platform ({self.service})",
            **self.headers,
        }
        data = None

        if form is not None:
            data = urllib.parse.urlencode(form).encode()
            headers["content-type"] = "application/x-www-form-urlencoded"
        elif body is not None:
            data = json.dumps(body).encode()
            headers["content-type"] = "application/json"

        req = urllib.request.Request(
            self.url(path, query), data=data, method=method, headers=headers
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                return Response(
                    res.status,
                    _decode(res.read()),
                    {k.lower(): v for k, v in res.headers.items()},
                )
        except urllib.error.HTTPError as e:
            return Response(e.code, _decode(e.read()), {})
        except urllib.error.URLError as e:
            raise AccessError(
                f"{self.service}: cannot reach {urllib.parse.urlsplit(self.base).netloc}: {e.reason}"
            ) from e

    def call(
        self,
        method: str,
        path: str,
        body: Any = None,
        query: Optional[dict[str, Any]] = None,
        form: Optional[dict[str, Any]] = None,
        ok: tuple[int, ...] = (),
    ) -> Any:
        res = self.send(method, path, body, query, form)

        if res.status >= 400 and res.status not in ok:
            raise AccessError(
                f"{self.service}: {method} {urllib.parse.urlsplit(self.url(path)).path} answered {res.status}: {_detail(res.data)}"
            )

        return res.data

    def pages(self, path: str, query: Optional[dict[str, Any]] = None) -> Iterator[Any]:
        """Every item of a listing that pages through a `Link: rel="next"` header — GitHub's and Sentry's."""
        url: Optional[str] = self.url(path, query)

        while url:
            res = self.send("GET", url)

            if res.status >= 400:
                raise AccessError(
                    f"{self.service}: GET {urllib.parse.urlsplit(url).path} answered {res.status}: {_detail(res.data)}"
                )

            yield from res.data or []
            url = _next(res.headers.get("link", ""))


def _next(link: str) -> Optional[str]:
    for target, results in LINK.findall(link):
        if results != "false":
            return target

    return None


def _decode(raw: bytes) -> Any:
    if not raw:
        return None

    try:
        return json.loads(raw)
    except ValueError:
        return raw.decode(errors="replace")[:300]


def _detail(data: Any) -> str:
    if isinstance(data, dict):
        for key in ("detail", "message", "error"):
            if data.get(key):
                return str(data[key])[:300]

    return str(data)[:300] if data else "no body"
