"""Dashboard and timeline, shaped for the API, with a short cache on the dashboard."""

from __future__ import annotations

import threading
import time
from typing import Any, Optional

from sqlalchemy.orm import Session as DbSession

from app.core.errors import Invalid, NotFound
from app.repositories.insights import EVENT_KINDS, Insights

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

            cached = hit[1] if hit and time.monotonic() - hit[0] < TTL else None

        if cached is None or fresh:
            cached = self.insights.dashboard(organization_id, project_id, app_id)

            with _lock:
                _cache[key] = (time.monotonic(), cached)

        return {
            **cached,
            "in_progress": self.insights.in_progress(
                organization_id, project_id, app_id
            ),
        }

    def app_activity(
        self,
        organization_id: str,
        project_id: str,
        app_id: str,
        kind: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if kind and kind not in EVENT_KINDS:
            raise Invalid(f"kind must be one of {', '.join(EVENT_KINDS)}")

        return self.insights.app_events(
            organization_id,
            project_id,
            app_id,
            (kind,) if kind else EVENT_KINDS,
            max(1, min(int(limit), 100)),
        )

    def timeline(self, app_id: str, tag: str) -> dict[str, Any]:
        found = self.insights.timeline(app_id, tag)

        if found is None:
            raise NotFound(f"no release {tag!r} on this app")

        return found
