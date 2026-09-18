"""Dashboard and timeline, shaped for the API, with a short cache on the dashboard."""

from __future__ import annotations

import threading
import time
from typing import Any, Optional

from sqlalchemy.orm import Session as DbSession

from app.core.errors import NotFound
from app.repositories.insights import Insights

TTL = 30.0
_cache: dict[str, tuple[float, dict]] = {}
_lock = threading.Lock()


class InsightsService:
    def __init__(self, db: DbSession) -> None:
        self.insights = Insights(db)

    def dashboard(
        self,
        organization_id: str,
        project_id: Optional[str] = None,
        app_id: Optional[str] = None,
        fresh: bool = False,
    ) -> dict[str, Any]:
        key = f"{organization_id}:{project_id or ''}:{app_id or ''}"

        with _lock:
            hit = _cache.get(key)

            if hit and not fresh and time.monotonic() - hit[0] < TTL:
                return hit[1]

        data = self.insights.dashboard(organization_id, project_id, app_id)

        with _lock:
            _cache[key] = (time.monotonic(), data)

        return data

    def timeline(self, app_id: str, tag: str) -> dict[str, Any]:
        found = self.insights.timeline(app_id, tag)

        if found is None:
            raise NotFound(f"no release {tag!r} on this app")

        return found
