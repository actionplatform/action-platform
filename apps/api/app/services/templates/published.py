"""Catalogs their repositories publish — the templates matrix and the plugins index — as `index.json` fetched raw and revalidated with its ETag."""

import json
import logging
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Optional

from action_platform.settings import settings

log = logging.getLogger("action_platform.catalog")
TIMEOUT = 5


class TemplatesIndex:
    def __init__(
        self, url: str | Callable[[], str] = "", ttl: Optional[int] = None
    ) -> None:
        self._url = url
        self._ttl = ttl
        self.lock = threading.Lock()
        self.cached: Optional[dict[str, Any]] = None
        self.etag = ""
        self.fetched_at = 0.0

    @property
    def url(self) -> str:
        """Read when asked, not when the module is imported — the settings are not loaded yet then."""
        if callable(self._url):
            return self._url()

        return self._url or settings.templates.index_url

    @property
    def ttl(self) -> int:
        return settings.templates.index_ttl if self._ttl is None else self._ttl

    @property
    def raw_base(self) -> str:
        return self.url.rsplit("/", 1)[0]

    def absolute(self, path: Optional[str]) -> Optional[str]:
        if not path:
            return None

        if path.startswith("http://") or path.startswith("https://"):
            return path

        return f"{self.raw_base}/{path.lstrip('/')}"

    def get(self) -> Optional[dict[str, Any]]:
        with self.lock:
            fresh = (
                self.cached is not None
                and time.monotonic() - self.fetched_at < self.ttl
            )

            if fresh:
                return self.cached

            headers = {"accept": "application/json", "user-agent": "action-platform"}

            if self.etag and self.cached is not None:
                headers["if-none-match"] = self.etag

            try:
                request = urllib.request.Request(self.url, headers=headers)

                with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                    self.cached = json.loads(response.read())
                    self.etag = response.headers.get("etag", "")
                    self.fetched_at = time.monotonic()
            except urllib.error.HTTPError as e:
                if e.code == 304:
                    self.fetched_at = time.monotonic()
                else:
                    log.warning("templates index %s unavailable: %s", self.url, e)
            except (urllib.error.URLError, ValueError, OSError) as e:
                log.warning("templates index %s unavailable: %s", self.url, e)

            return self.cached


index = TemplatesIndex()
plugins_index = TemplatesIndex(lambda: settings.templates.plugins_index_url)
