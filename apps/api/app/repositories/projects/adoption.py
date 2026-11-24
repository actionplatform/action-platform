"""Where each app stands on the way onto the platform."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select

from app.core.db.models import AppAdoption, PullRequest
from app.core.shared.clock import now
from app.repositories.base import DirectoryBase

DETAILS = ("language", "ci", "version", "branch")
FIELDS = ("state", "reason", "pull_request_number", "pull_request_url", *DETAILS)


class AdoptionStore(DirectoryBase):
    def of(self, app_ids: list[str]) -> dict[str, AppAdoption]:
        if not app_ids:
            return {}

        return {
            row.app_id: row
            for row in self.db.scalars(
                select(AppAdoption).where(AppAdoption.app_id.in_(app_ids))
            )
        }

    def record(self, app_id: str, keep: bool = False, **fields: Any) -> AppAdoption:
        """`keep` leaves what an earlier run found about the app (language, CI, version, branch) when this one did not look."""
        row = self.db.get(AppAdoption, app_id)

        if row is None:
            row = AppAdoption(app_id=app_id)
            self.db.add(row)

        for name in FIELDS:
            if keep and name in DETAILS and fields.get(name) is None:
                continue

            setattr(row, name, fields.get(name))

        row.checked_at = now()
        self.db.flush()

        return row

    def pull_request_state(self, app_id: str, number: Optional[int]) -> Optional[str]:
        """The state the code host last reported for that pull request, once its activity was imported."""
        if number is None:
            return None

        return self.db.scalar(
            select(PullRequest.state).where(
                PullRequest.app_id == app_id, PullRequest.number == number
            )
        )

    def open_pull_request(
        self, app_id: str, row: Optional[AppAdoption], branch: str
    ) -> Optional[dict[str, Any]]:
        """The install pull request still open for the app: the one a run opened, else one the code host reported from `branch`."""
        if (
            row is not None
            and row.state == "pr_open"
            and row.pull_request_number is not None
            and self.pull_request_state(app_id, row.pull_request_number)
            in (None, "open")
        ):
            return {"number": row.pull_request_number, "url": row.pull_request_url}

        found = self.db.scalar(
            select(PullRequest)
            .where(
                PullRequest.app_id == app_id,
                PullRequest.head == branch,
                PullRequest.state == "open",
            )
            .order_by(PullRequest.number.desc())
        )

        return {"number": found.number, "url": found.url} if found else None
