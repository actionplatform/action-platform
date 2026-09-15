"""Outbound HTTP to code hosts: JSON in and out, provider errors named after the host that answered."""

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from action_platform.core.exception import ProviderError

TIMEOUT = 15
USER_AGENT = "action-platform"


class BasicAuth:
    @staticmethod
    def header(user: str, password: str) -> str:
        return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


class HttpClient:
    def __init__(self, timeout: int = TIMEOUT) -> None:
        self.timeout = timeout

    def get_json(self, url: str, headers: Optional[dict[str, str]] = None) -> Any:
        return self._send(self._request(url, headers=headers))

    def post_json(
        self, url: str, body: Any, headers: Optional[dict[str, str]] = None
    ) -> Any:
        request = self._request(
            url,
            data=json.dumps(body).encode(),
            method="POST",
            headers={"content-type": "application/json", **(headers or {})},
        )

        return self._send(request)

    def post_form(
        self, url: str, form: dict[str, str], headers: Optional[dict[str, str]] = None
    ) -> dict[str, Any]:
        request = self._request(
            url,
            data=urllib.parse.urlencode(form).encode(),
            method="POST",
            headers={
                "content-type": "application/x-www-form-urlencoded",
                **(headers or {}),
            },
        )

        return self._send(request) or {}

    def get_pages(
        self, url: str, headers: dict[str, str], limit: int = 20
    ) -> list[Any]:
        """Every row of a `per_page`/`page` paginated listing (GitHub, GitLab), up to `limit` pages."""
        out: list[Any] = []
        separator = "&" if "?" in url else "?"

        for page in range(1, limit + 1):
            rows = self.get_json(f"{url}{separator}per_page=100&page={page}", headers)

            if not isinstance(rows, list):
                break

            out.extend(rows)

            if len(rows) < 100:
                break

        return out

    def get_values(self, url: str, headers: dict[str, str]) -> list[Any]:
        """Every row of a `values`/`next` paginated listing (Bitbucket)."""
        out: list[Any] = []
        next_url: Optional[str] = url

        while next_url:
            data = self.get_json(next_url, headers)
            out.extend(data.get("values", []))
            next_url = data.get("next")

        return out

    @staticmethod
    def _request(
        url: str,
        data: Optional[bytes] = None,
        method: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> urllib.request.Request:
        return urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "accept": "application/json",
                "user-agent": USER_AGENT,
                **(headers or {}),
            },
        )

    def _send(self, request: urllib.request.Request) -> Any:
        host = urllib.parse.urlparse(request.full_url).netloc

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read() or b"null")
        except urllib.error.HTTPError as e:
            raise ProviderError(f"{e.code} from {host}") from e
        except urllib.error.URLError as e:
            raise ProviderError(f"cannot reach {host}: {e.reason}") from e


http = HttpClient()
