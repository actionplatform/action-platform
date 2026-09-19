"""A target whose deploy is a run of the repository's own CI: the platform decides when and where, the pipeline publishes.

    [[deploy.targets]]
    name = "pypi"
    kind = "pypi"
    run_by = "github_actions"
    workflow = "publish.yml"
    package = "my-lib"

`deploy` starts `workflow` on the release tag with `version` and `registry` (the scope) as inputs, follows the run to its end and asks the registry whether the version arrived. No credential of the registry reaches the platform: the pipeline holds them (trusted publishing, OIDC)."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from action_platform.abc.ci_runner import CIRunner
from action_platform.abc.deploy_target import DeployTarget
from action_platform.core.context import (
    Check,
    Context,
    DeployResult,
    Diagnosis,
    Run,
    RunRef,
)
from action_platform.core.exception import DeployError, ProviderError
from action_platform.logging import logger

FINAL = ("success", "failure", "unstable", "aborted")
POLL_SECONDS = 10
TIMEOUT_SECONDS = 1800


class DispatchedTarget(DeployTarget):
    def __init__(self, inner: DeployTarget, runner: CIRunner, job: str) -> None:
        self.inner = inner
        self.runner = runner
        self.job = job
        self.name = inner.name

    def preflight(self, ctx: Context) -> None:
        if not self.job:
            raise DeployError(
                f"{self.name}: run by {self.runner.name} but no workflow or job named"
            )

        try:
            self.runner.test()
        except ProviderError as e:
            raise DeployError(f"{self.name}: {self.runner.name} refused: {e}") from e

    def deploy(self, ctx: Context) -> DeployResult:
        ref = ctx.tag or f"v{ctx.next_version}"
        params = {"version": ctx.next_version, "registry": ctx.stage}
        logger.info(
            "dispatch %s on %s (%s) version=%s registry=%s",
            self.job,
            ref,
            self.runner.name,
            ctx.next_version,
            ctx.stage,
        )
        started = datetime.now(timezone.utc)

        try:
            ref_ = self.runner.start(self.job, ref, params)
            run = self.follow(
                ref_,
                ref,
                started,
                int(ctx.env.get("AP_DISPATCH_TIMEOUT", TIMEOUT_SECONDS)),
            )
        except ProviderError as e:
            return DeployResult(
                ok=False, target=self.name, version=ctx.next_version, error=str(e)
            )

        if run.status != "success":
            return DeployResult(
                ok=False,
                target=self.name,
                version=ctx.next_version,
                url=run.url,
                error=f"{self.runner.name} run ended {run.status}",
            )

        published = self._verify(ctx.next_version, ctx.stage)

        return DeployResult(
            ok=published is not False,
            target=self.name,
            version=ctx.next_version,
            url=self.inner.url(ctx.next_version, ctx.stage) or run.url,
            error=None
            if published is not False
            else f"the run succeeded but {ctx.next_version} is not at {self.name}",
        )

    def follow(self, ref: RunRef, tag: str, since: datetime, timeout: int) -> Run:
        """The run `ref` points at, polled until it ends. A dispatch that returns no run id (GitHub) is found among the job's runs started on `tag` after `since`."""
        deadline = time.monotonic() + timeout
        last = None

        while True:
            run = self._locate(ref, tag, since)

            if run is not None and run.status != last:
                logger.info(
                    "run %s: %s%s",
                    run.number,
                    run.status,
                    f" {run.url}" if run.url else "",
                )
                last = run.status

            if run is not None and run.status in FINAL:
                return run

            if time.monotonic() > deadline:
                raise ProviderError(
                    f"{self.job} did not finish within {timeout}s"
                    if run
                    else f"no run of {self.job} appeared on {tag} within {timeout}s"
                )

            time.sleep(POLL_SECONDS)

    def _locate(self, ref: RunRef, tag: str, since: datetime) -> Run | None:
        if ref.id.isdigit():
            return self.runner.run(self.job, int(ref.id))

        for run in self.runner.runs(self.job, limit=20):
            if (
                run.branch == tag
                and run.started_at
                and run.started_at >= since.replace(microsecond=0)
            ):
                return run

        return None

    def _verify(self, version: str, stage: str) -> bool | None:
        try:
            return self.inner.verify(version, stage)
        except NotImplementedError:
            return None
        except ProviderError as e:
            logger.warning("%s: could not verify %s: %s", self.name, version, e)
            return None

    def readiness(self, ctx: Context) -> list[Check]:
        checks = []

        try:
            self.runner.test()
            checks.append(
                Check(
                    "ci.reachable",
                    True,
                    f"{self.runner.name} answers for {self.job}",
                    target=self.name,
                )
            )
        except ProviderError as e:
            checks.append(
                Check(
                    "ci.reachable",
                    False,
                    str(e),
                    fix="reconnect the source host; the deploy starts the workflow with its token",
                    target=self.name,
                )
            )

        if not self.job:
            checks.append(
                Check(
                    "ci.workflow",
                    False,
                    f"{self.name} names no workflow",
                    level="static",
                    fix='add workflow = "publish.yml" to the target in platform.toml',
                    target=self.name,
                )
            )

        for check in self.inner.readiness(ctx):
            check.target = check.target or self.name
            checks.append(check)

        return checks

    def diagnose(self, ctx: Context) -> Diagnosis:
        published = self._verify(ctx.current_version, ctx.stage)

        return Diagnosis(
            ok=published is not False,
            target=self.name,
            status="published"
            if published
            else "not published"
            if published is False
            else "unknown",
            version=ctx.current_version,
            url=self.inner.url(ctx.current_version, ctx.stage),
        )

    def verify(self, version: str, stage: str | None = None) -> bool:
        return self.inner.verify(version, stage)

    def url(self, version: str, stage: str | None = None) -> str | None:
        return self.inner.url(version, stage)
