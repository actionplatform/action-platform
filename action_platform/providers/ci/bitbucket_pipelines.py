"""Bitbucket Pipelines CIRunner provider: pipelines of a repository, with the source host's credentials.

`job` is unused — one pipelines configuration per repository.
"""

from __future__ import annotations

import base64
from datetime import datetime

from action_platform.abc.ci_runner import CIRunner
from action_platform.core.context import Run, RunRef
from action_platform.core.exception import ProviderError
from action_platform.providers.source import rest

RESULTS = {
    "SUCCESSFUL": "success",
    "FAILED": "failure",
    "ERROR": "failure",
    "STOPPED": "aborted",
    "EXPIRED": "aborted",
}
STATES = {
    "PENDING": "queued",
    "IN_PROGRESS": "running",
    "PAUSED": "queued",
    "HALTED": "queued",
}


def _utc(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


class CIBitbucket(CIRunner):
    """
    Args:
        repo (str): "workspace/repo_slug".
        token (str): an app password (with `username`) or an access token.
        username (str | None): the user the app password belongs to.
    """

    name = "bitbucket_pipelines"
    embedded = True

    def __init__(
        self,
        repo: str,
        token: str | None = None,
        username: str | None = None,
        base_url: str | None = None,
    ) -> None:
        if not repo:
            raise ProviderError("bitbucket_pipelines needs a repository")

        self.repo = repo
        self.token = token
        self.username = username
        self.api = "https://api.bitbucket.org/2.0"

    def _headers(self) -> dict[str, str]:
        if self.token and self.username and self.username != "x-token-auth":
            raw = base64.b64encode(f"{self.username}:{self.token}".encode()).decode()

            return {"authorization": f"Basic {raw}"}

        return {"authorization": f"Bearer {self.token}"} if self.token else {}

    def test(self) -> None:
        rest.call("GET", f"{self.api}/repositories/{self.repo}", self._headers())

    def runs(self, job: str, limit: int = 50) -> list[Run]:
        url = f"{self.api}/repositories/{self.repo}/pipelines/?sort=-created_on&pagelen={min(int(limit), 100)}"
        payload = rest.call("GET", url, self._headers()) or {}

        return [self._run(p) for p in payload.get("values") or []]

    def run(self, job: str, number: int) -> Run:
        return self._run(
            rest.call(
                "GET",
                f"{self.api}/repositories/{self.repo}/pipelines/{int(number)}",
                self._headers(),
            )
            or {}
        )

    def start(self, job: str, ref: str, params: dict | None = None) -> RunRef:
        body = {
            "target": {
                "type": "pipeline_ref_target",
                "ref_type": "branch",
                "ref_name": ref,
            },
            "variables": [
                {"key": k, "value": str(v)} for k, v in (params or {}).items()
            ],
        }
        created = (
            rest.call(
                "POST",
                f"{self.api}/repositories/{self.repo}/pipelines/",
                self._headers(),
                body,
            )
            or {}
        )

        return RunRef(
            id=str(created.get("build_number", "")),
            url=((created.get("links") or {}).get("html") or {}).get("href"),
        )

    def _run(self, item: dict) -> Run:
        state = item.get("state") or {}
        result = (state.get("result") or {}).get("name")
        status = RESULTS.get(result or "", None) or STATES.get(
            state.get("name") or "", "unknown"
        )
        target = item.get("target") or {}
        started = _utc(item.get("created_on"))
        seconds = item.get("duration_in_seconds")

        return Run(
            number=int(item["build_number"]),
            status=status,
            url=f"https://bitbucket.org/{self.repo}/pipelines/results/{item['build_number']}",
            branch=target.get("ref_name"),
            sha=(target.get("commit") or {}).get("hash"),
            trigger=(item.get("trigger") or {}).get("name"),
            started_at=started,
            duration_ms=int(seconds * 1000) if seconds else None,
            name=f"#{item['build_number']}",
        )
