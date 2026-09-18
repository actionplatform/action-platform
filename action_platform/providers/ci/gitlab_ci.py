"""GitLab CI CIRunner provider: pipelines of a project, with the source host's token.

`job` is unused — GitLab has one pipeline per project; a non-empty value filters by ref.
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

from action_platform.abc.ci_runner import CIRunner
from action_platform.core.context import Run, RunRef
from action_platform.core.exception import ProviderError
from action_platform.providers.source import rest

STATUSES = {
    "created": "queued",
    "waiting_for_resource": "queued",
    "preparing": "queued",
    "pending": "queued",
    "scheduled": "queued",
    "running": "running",
    "success": "success",
    "failed": "failure",
    "canceled": "aborted",
    "skipped": "aborted",
    "manual": "queued",
}


def _utc(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


class CIGitlab(CIRunner):
    """
    Args:
        repo (str): "group/project".
        token (str): the source host's token.
        base_url (str | None): a self-hosted GitLab, e.g. https://gitlab.example.com.
    """

    name = "gitlab_ci"
    embedded = True

    def __init__(
        self, repo: str, token: str | None = None, base_url: str | None = None
    ) -> None:
        if not repo:
            raise ProviderError("gitlab_ci needs a project")

        self.repo = repo
        self.web = (base_url or "https://gitlab.com").rstrip("/")
        self.api = f"{self.web}/api/v4"
        self.token = token

    def _headers(self) -> dict[str, str]:
        return {"authorization": f"Bearer {self.token}"} if self.token else {}

    @property
    def _project(self) -> str:
        return f"{self.api}/projects/{quote(self.repo, safe='')}"

    def test(self) -> None:
        rest.call("GET", self._project, self._headers())

    def runs(self, job: str, limit: int = 50) -> list[Run]:
        url = f"{self._project}/pipelines?per_page={min(int(limit), 100)}&order_by=id&sort=desc"

        if job:
            url += f"&ref={quote(job, safe='')}"

        return [self._run(p) for p in rest.call("GET", url, self._headers()) or []]

    def run(self, job: str, number: int) -> Run:
        return self._run(
            rest.call(
                "GET", f"{self._project}/pipelines/{int(number)}", self._headers()
            )
            or {}
        )

    def start(self, job: str, ref: str, params: dict | None = None) -> RunRef:
        body = {
            "ref": ref,
            "variables": [
                {"key": k, "value": str(v)} for k, v in (params or {}).items()
            ],
        }
        created = (
            rest.call("POST", f"{self._project}/pipeline", self._headers(), body) or {}
        )

        return RunRef(id=str(created.get("id", "")), url=created.get("web_url"))

    @staticmethod
    def _run(item: dict) -> Run:
        started = _utc(item.get("started_at") or item.get("created_at"))
        updated = _utc(item.get("updated_at"))
        status = STATUSES.get(item.get("status") or "", "unknown")
        duration = (
            int((updated - started).total_seconds() * 1000)
            if started and updated and status not in ("queued", "running")
            else None
        )

        return Run(
            number=int(item["id"]),
            status=status,
            url=item.get("web_url"),
            branch=item.get("ref"),
            sha=item.get("sha"),
            trigger=item.get("source"),
            started_at=started,
            duration_ms=duration,
            name=f"#{item.get('iid') or item['id']}",
        )
