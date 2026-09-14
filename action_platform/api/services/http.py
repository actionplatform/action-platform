import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from action_platform.core.exception import ProviderError

TIMEOUT = 15
USER_AGENT = "action-platform"


def basic(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def get_json(url: str, headers: Optional[dict[str, str]] = None) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "accept": "application/json",
            "user-agent": USER_AGENT,
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read() or b"null")
    except urllib.error.HTTPError as e:
        raise ProviderError(f"{e.code} from {urllib.parse.urlparse(url).netloc}") from e
    except urllib.error.URLError as e:
        raise ProviderError(
            f"cannot reach {urllib.parse.urlparse(url).netloc}: {e.reason}"
        ) from e


def post_form(
    url: str, form: dict[str, str], headers: Optional[dict[str, str]] = None
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(form).encode(),
        method="POST",
        headers={
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": USER_AGENT,
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise ProviderError(f"{e.code} from {urllib.parse.urlparse(url).netloc}") from e
    except urllib.error.URLError as e:
        raise ProviderError(
            f"cannot reach {urllib.parse.urlparse(url).netloc}: {e.reason}"
        ) from e


def get_pages(url: str, headers: dict[str, str], limit: int = 20) -> list[Any]:
    out: list[Any] = []
    separator = "&" if "?" in url else "?"
    for page in range(1, limit + 1):
        rows = get_json(f"{url}{separator}per_page=100&page={page}", headers)
        if not isinstance(rows, list):
            break
        out.extend(rows)
        if len(rows) < 100:
            break
    return out


def get_values(url: str, headers: dict[str, str]) -> list[Any]:
    out: list[Any] = []
    next_url: Optional[str] = url
    while next_url:
        data = get_json(next_url, headers)
        out.extend(data.get("values", []))
        next_url = data.get("next")
    return out
