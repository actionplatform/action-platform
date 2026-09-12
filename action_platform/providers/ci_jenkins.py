"""Jenkins CIRunner provider."""

from __future__ import annotations

from typing import Iterator

from action_platform.abc.ci_runner import CIRunner
from action_platform.core.context import Context, RunRef, RunResult


class CIJenkins(CIRunner):
    """
    Import:
        from action_platform.providers import CIJenkins

    Example:
        CIJenkins(url="https://jenkins.internal", job="my-job")

    Args:
        url (str): Jenkins base URL.
        job (str): job name.
        user (str): overrides ACTION_PLATFORM_JENKINS_USER env var.
        token (str): overrides ACTION_PLATFORM_JENKINS_TOKEN env var.
    """

    name = "jenkins"

    def __init__(
        self,
        url: str,
        job: str,
        user: str | None = None,
        token: str | None = None,
    ) -> None:
        self.url = url.rstrip("/")
        self.job = job
        self.user = user
        self.token = token

    def trigger(self, ctx: Context, job: str, params: dict) -> RunRef:
        raise NotImplementedError

    def wait(self, ctx: Context, run: RunRef, timeout: int = 1800) -> RunResult:
        raise NotImplementedError

    def logs(self, ctx: Context, run: RunRef) -> Iterator[str]:
        raise NotImplementedError
