"""The templates catalog as the repository publishes it: `index.json`, fetched raw and cached for a few minutes."""

import json
import logging
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Optional

from action_platform.settings import settings

log = logging.getLogger("action_platform.catalog")
TIMEOUT = 5


class TemplatesIndex:
    def __init__(self, url: str = "", ttl: Optional[int] = None) -> None:
        self.url = url or settings.TEMPLATES_INDEX_URL
        self.ttl = settings.TEMPLATES_INDEX_TTL if ttl is None else ttl
        self.lock = threading.Lock()
        self.cached: Optional[dict[str, Any]] = None
        self.fetched_at = 0.0

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

            try:
                request = urllib.request.Request(
                    self.url,
                    headers={
                        "accept": "application/json",
                        "user-agent": "action-platform",
                    },
                )

                with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                    self.cached = json.loads(response.read())
                    self.fetched_at = time.monotonic()
            except (urllib.error.URLError, ValueError, OSError) as e:
                log.warning("templates index %s unavailable: %s", self.url, e)

            return self.cached


index = TemplatesIndex()
