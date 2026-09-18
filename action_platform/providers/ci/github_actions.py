"""GitHub Actions CIRunner provider: workflow runs of a repository, with the source host's token.

`job` is a workflow file name (`ci.yml`) or empty for every workflow.
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

from action_platform.abc.ci_runner import CIRunner
from action_platform.core.context import Run
from action_platform.core.exception import ProviderError
from action_platform.providers.source import rest

STATUSES = {
    "queued": "queued",
    "waiting": "queued",
    "pending": "queued",
    "requested": "queued",
    "in_progress": "running",
}

CONCLUSIONS = {
    "success": "success",
    "failure": "failure",
    "timed_out": "failure",
    "startup_failure": "failure",
    "action_required": "failure",
    "neutral": "unstable",
    "cancelled": "aborted",
    "skipped": "aborted",
    "stale": "aborted",
}


def _utc(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


class CIGithubActions(CIRunner):
    """
    Args:
        repo (str): "owner/name".
        token (str): the source host's token.
        base_url (str | None): API root for GitHub Enterprise, e.g. https://ghe.example.com/api/v3.
    """

    name = "github_actions"
    embedded = True

    def __init__(
        self, repo: str, token: str | None = None, base_url: str | None = None
    ) -> None:
        if not repo:
            raise ProviderError("github_actions needs a repository")

        self.repo = repo
        self.token = token
        self.api = (base_url or "https://api.github.com").rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers = {"x-github-api-version": "2022-11-28"}

        if self.token:
            headers["authorization"] = f"Bearer {self.token}"

        return headers

    def test(self) -> None:
        rest.call("GET", f"{self.api}/repos/{self.repo}", self._headers())

    def runs(self, job: str, limit: int = 50) -> list[Run]:
        base = f"{self.api}/repos/{self.repo}/actions"
        url = (
            f"{base}/workflows/{quote(job, safe='')}/runs" if job else f"{base}/runs"
        ) + f"?per_page={min(int(limit), 100)}"
        payload = rest.call("GET", url, self._headers()) or {}

        return [self._run(r) for r in payload.get("workflow_runs") or []]

    def run(self, job: str, number: int) -> Run:
        url = f"{self.api}/repos/{self.repo}/actions/runs/{int(number)}"

        return self._run(rest.call("GET", url, self._headers()) or {})

    @staticmethod
    def _run(item: dict) -> Run:
        if item.get("status") == "completed":
            status = CONCLUSIONS.get(item.get("conclusion") or "", "unknown")
        else:
            status = STATUSES.get(item.get("status") or "", "unknown")

        started = _utc(item.get("run_started_at") or item.get("created_at"))
        updated = _utc(item.get("updated_at"))
        duration = (
            int((updated - started).total_seconds() * 1000)
            if started and updated and status not in ("queued", "running")
            else None
        )

        return Run(
            number=int(item["id"]),
            status=status,
            url=item.get("html_url"),
            branch=item.get("head_branch"),
            sha=item.get("head_sha"),
            trigger=item.get("event"),
            started_at=started,
            duration_ms=duration,
            name=item.get("name"),
        )
