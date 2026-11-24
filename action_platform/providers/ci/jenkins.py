"""Jenkins CIRunner provider: builds of a job through the JSON API.

`job` is the path Jenkins shows in the URL, slashes for folders and
multibranch branches: `team/app` or `team/app/main`.
"""

from __future__ import annotations

import base64
import re
from datetime import datetime, timezone
from urllib.parse import quote, urlencode

from action_platform.abc.ci_runner import CIRunner
from action_platform.core.context import Run, RunRef
from action_platform.core.exception import DeployError, ProviderError
from action_platform.providers.source import rest

TREE = (
    "builds[number,result,building,timestamp,duration,url,displayName,"
    "actions[lastBuiltRevision[SHA1,branch[name]],causes[shortDescription],"
    "parameters[name,value]]]"
)

QUEUE_ITEM = re.compile(r"/queue/item/(\d+)")

RESULTS = {
    "SUCCESS": "success",
    "FAILURE": "failure",
    "UNSTABLE": "unstable",
    "ABORTED": "aborted",
    "NOT_BUILT": "aborted",
}


class CIJenkins(CIRunner):
    """
    Args:
        base_url (str): the Jenkins root, e.g. https://ci.example.com.
        token (str): the user's API token.
        username (str): the user the token belongs to.
    """

    name = "jenkins"

    def __init__(
        self, base_url: str, token: str | None = None, username: str | None = None
    ) -> None:
        if not base_url:
            raise ProviderError("jenkins needs a base_url")

        self.base_url = base_url.rstrip("/")
        self.token = token
        self.username = username
        self._builds: dict[str, int] = {}

    def _headers(self) -> dict[str, str]:
        if not self.token:
            return {}

        raw = base64.b64encode(f"{self.username or ''}:{self.token}".encode()).decode()

        return {"authorization": f"Basic {raw}"}

    def _job_url(self, job: str) -> str:
        parts = [quote(p, safe="") for p in job.strip("/").split("/") if p]

        if not parts:
            raise ProviderError("jenkins needs a job path")

        return self.base_url + "".join(f"/job/{p}" for p in parts)

    def test(self) -> None:
        rest.call("GET", f"{self.base_url}/api/json?tree=mode", self._headers())

    def runs(self, job: str, limit: int = 50) -> list[Run]:
        url = f"{self._job_url(job)}/api/json?tree={TREE}{{0,{int(limit)}}}"
        payload = rest.call("GET", url, self._headers()) or {}

        return [self._run(b) for b in payload.get("builds") or []]

    def run(self, job: str, number: int) -> Run:
        url = f"{self._job_url(job)}/{int(number)}/api/json?tree={TREE[7:-1]}"

        return self._run(rest.call("GET", url, self._headers()) or {})

    @staticmethod
    def _run(build: dict) -> Run:
        sha = branch = trigger = None
        params: dict[str, str] = {}

        for action in build.get("actions") or []:
            revision = action.get("lastBuiltRevision") or {}

            if revision:
                sha = revision.get("SHA1") or sha
                names = revision.get("branch") or []
                branch = (names[0].get("name") if names else None) or branch

            causes = action.get("causes") or []

            if causes and not trigger:
                trigger = causes[0].get("shortDescription")

            for param in action.get("parameters") or []:
                if param.get("name") and param.get("value") is not None:
                    params[str(param["name"])] = str(param["value"])

        if branch and "/" in branch:
            branch = branch.split("/", 1)[1]

        if build.get("building"):
            status = "running"
        else:
            status = RESULTS.get(build.get("result") or "", "unknown")

        timestamp = build.get("timestamp")

        return Run(
            number=int(build["number"]),
            status=status,
            url=build.get("url"),
            branch=branch,
            sha=sha,
            trigger=trigger,
            started_at=(
                datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
                if timestamp
                else None
            ),
            duration_ms=build.get("duration") or None,
            name=build.get("displayName"),
            params=params,
        )

    def start(self, job: str, ref: str, params: dict | None = None) -> RunRef:
        """Queue a build: `REF` set to `ref` when there is one, plus `params`. The run's id is its queue item, which `run_of` turns into the build."""
        url = self._job_url(job)
        query = {**({"REF": ref} if ref else {}), **(params or {})}
        headers = self._headers()

        try:
            crumb = (
                rest.call("GET", f"{self.base_url}/crumbIssuer/api/json", headers) or {}
            )
            headers[crumb.get("crumbRequestField", "Jenkins-Crumb")] = crumb.get(
                "crumb", ""
            )
        except ProviderError:
            pass

        path = "/buildWithParameters" if query else "/build"
        queued = rest.location(
            "POST",
            url + path + ("?" + urlencode(query) if query else ""),
            headers,
            ok=(200, 201, 202),
        )
        item = QUEUE_ITEM.search(queued or "")

        return RunRef(
            id=f"queue:{item.group(1)}" if item else f"{job}@{ref}",
            url=url,
        )

    def run_of(self, job: str, ref: RunRef) -> Run | None:
        """The build a queue item became; None while it waits. A cancelled item is an error."""
        if not ref.id.startswith("queue:"):
            raise NotImplementedError(f"{job} was started without a queue item")

        number = self._builds.get(ref.id)

        if number is None:
            item = (
                rest.call(
                    "GET",
                    f"{self.base_url}/queue/item/{ref.id[6:]}/api/json",
                    self._headers(),
                )
                or {}
            )

            if item.get("cancelled"):
                raise DeployError(f"the build of {job} was cancelled in the queue")

            number = (item.get("executable") or {}).get("number")

            if number is None:
                return None

            self._builds[ref.id] = int(number)

        return self.run(job, int(number))

    def stages(self, job: str, number: int) -> list[tuple[str, str]]:
        """The pipeline's stages from `wfapi/describe`, in order."""
        payload = (
            rest.call(
                "GET",
                f"{self._job_url(job)}/{int(number)}/wfapi/describe",
                self._headers(),
            )
            or {}
        )

        return [
            (str(s.get("name")), str(s.get("status")))
            for s in payload.get("stages") or []
            if s.get("name")
        ]
