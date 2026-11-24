"""A target whose deploy is a run of the repository's own CI: the platform decides when and where, the pipeline publishes.

    [[deploy.targets]]
    name = "pypi"
    kind = "pypi"
    run_by = "github_actions"
    workflow = "publish.yml"
    package = "my-lib"

`deploy` starts `workflow` on the release tag with `version` and `registry` as inputs — the registry the kind pairs with the scope's criticality (`testpypi` for a `test` scope, `pypi` otherwise), or the target's `registry` option — follows the run to its end and asks the registry whether the version arrived. No credential of the registry reaches the platform: the pipeline holds them (trusted publishing, OIDC).

A job that takes the release as a parameter (`version_parameter`, a Jenkins job) is started with that parameter alone, set to the tag; its result is the deploy's, and the row links to the build — the destination is asked later, on Sync."""

from __future__ import annotations

import time
from dataclasses import replace
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
from action_platform.core.exception import (
    ActionPlatformError,
    DeployError,
    ProviderError,
)
from action_platform.logging import logger
from action_platform.providers.deploy.pipeline_published import (
    PipelinePublishedTarget,
)

FINAL = ("success", "failure", "unstable", "aborted")
POLL_SECONDS = 10
TIMEOUT_SECONDS = 3600


class DispatchedTarget(DeployTarget):
    def __init__(
        self,
        inner: DeployTarget,
        runner: CIRunner,
        job: str,
        registry: str = "",
        version_parameter: str = "",
    ) -> None:
        self.inner = inner
        self.runner = runner
        self.job = job
        self.name = inner.name
        self.fixed_registry = registry
        self.version_parameter = version_parameter

    def preflight(self, ctx: Context) -> None:
        if not self.job:
            raise DeployError(
                f"{self.name}: run by {self.runner.name} but no workflow or job named"
            )

        if self.runner.name == "jenkins" and not self.version_parameter:
            raise DeployError(
                f"{self.name}: a Jenkins job takes the release through a parameter; set version_parameter"
            )

        try:
            self.runner.test()
        except ProviderError as e:
            raise DeployError(f"{self.name}: {self.runner.name} refused: {e}") from e

    def registry(self, ctx: Context) -> str:
        if self.fixed_registry:
            return self.fixed_registry

        if hasattr(self.inner, "registry_for"):
            return self.inner.registry_for(ctx.criticality)

        return self.name

    def parameters(self, ctx: Context, ref: str) -> tuple[str, dict[str, str]]:
        """The ref the run starts on and its parameters: the release in `version_parameter` alone for a job that takes it, else the tag with `version` and `registry`."""
        if self.version_parameter:
            return "", {self.version_parameter: ref}

        return ref, {"version": ctx.next_version, "registry": self.registry(ctx)}

    def deploy(self, ctx: Context) -> DeployResult:
        ref = ctx.tag or f"v{ctx.next_version}"
        registry = self.registry(ctx)
        on, params = self.parameters(ctx, ref)
        logger.info(
            "dispatch %s on %s (%s) version=%s registry=%s scope=%s",
            self.job,
            ref,
            self.runner.name,
            ctx.next_version,
            registry,
            ctx.stage,
        )
        started = datetime.now(timezone.utc)

        try:
            ref_ = self.runner.start(self.job, on, params)
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

        if self.version_parameter:
            return DeployResult(
                ok=True, target=self.name, version=ctx.next_version, url=run.url
            )

        published = self._verify(ctx.next_version, registry)

        return DeployResult(
            ok=published is not False,
            target=self.name,
            version=ctx.next_version,
            url=self.inner.url(ctx.next_version, registry) or run.url,
            error=None
            if published is not False
            else f"the run succeeded but {ctx.next_version} is not at {self.name}",
        )

    def follow(self, ref: RunRef, tag: str, since: datetime, timeout: int) -> Run:
        """The run `ref` points at, polled until it ends. A dispatch that returns no run id (GitHub) is found among the job's runs started on `tag` after `since`; each stage of the run is logged as it changes."""
        deadline = time.monotonic() + timeout
        last = None
        seen: dict[str, str] = {}

        while True:
            try:
                run = self._locate(ref, tag, since)
            except (ProviderError, OSError) as e:
                if time.monotonic() > deadline:
                    raise ProviderError(f"{self.job}: {e}") from e

                logger.warning("run of %s: %s; asking again", self.job, e)
                time.sleep(POLL_SECONDS)
                continue

            if run is not None and run.status != last:
                logger.info(
                    "run %s: %s%s",
                    run.number,
                    run.status,
                    f" {run.url}" if run.url else "",
                )
                last = run.status

            if run is not None:
                self._stages(run, seen)

            if run is not None and run.status in FINAL:
                return run

            if time.monotonic() > deadline:
                raise ProviderError(
                    f"{self.job} did not finish within {timeout}s"
                    if run
                    else f"no run of {self.job} appeared on {tag} within {timeout}s"
                )

            time.sleep(POLL_SECONDS)

    def _stages(self, run: Run, seen: dict[str, str]) -> None:
        try:
            stages = self.runner.stages(self.job, run.number)
        except (NotImplementedError, ProviderError):
            return

        for name, status in stages:
            if seen.get(name) != status:
                logger.info("run %s: stage %s %s", run.number, name, status)
                seen[name] = status

    def _locate(self, ref: RunRef, tag: str, since: datetime) -> Run | None:
        try:
            return self.runner.run_of(self.job, ref)
        except NotImplementedError:
            pass

        if ref.id.isdigit():
            return self.runner.run(self.job, int(ref.id))

        for run in self.runner.runs(self.job, limit=20):
            named = (
                run.params.get(self.version_parameter) == tag
                if self.version_parameter
                else run.branch == tag
            )

            if (
                named
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
        except ActionPlatformError as e:
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

        if isinstance(self.inner, PipelinePublishedTarget):
            for check in self.inner.readiness(replace(ctx, stage=self.registry(ctx))):
                check.target = check.target or self.name
                checks.append(check)

        return checks

    def diagnose(self, ctx: Context) -> Diagnosis:
        registry = self.registry(ctx)
        published = self._verify(ctx.current_version, registry)

        return Diagnosis(
            ok=published is not False,
            target=self.name,
            status="published"
            if published
            else "not published"
            if published is False
            else "unknown",
            version=ctx.current_version,
            url=self.inner.url(ctx.current_version, registry),
        )

    def verify(self, version: str, stage: str | None = None) -> bool:
        return self.inner.verify(version, stage)

    def url(self, version: str, stage: str | None = None) -> str | None:
        return self.inner.url(version, stage)
