"""An app's pipelines read live from its CI: the jobs it names, their runs, and one run's stages, log, tests and artifacts — passed through to the member, never stored."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Iterator, Optional, TypeVar

from action_platform.abc.ci_runner import CIRunner
from action_platform.core.context import Run
from action_platform.core.exception import ActionPlatformError
from app.core.db.models import App
from app.core.errors import Invalid, NotFound, Upstream
from app.schemas import ci as schemas
from app.services.ci.redact import redact
from app.services.ci.service import CiService
from app.services.workspace.app_context import AppContext

MAX_LOG_BYTES = 256 * 1024
MAX_DOWNLOAD_READS = 10_000
RUNS_PER_JOB = 25
MAX_RUNS = 100
MAX_FAILURES = 200
MAX_STACK = 16 * 1024
LIVE = ("queued", "running")
EPOCH = datetime.min.replace(tzinfo=timezone.utc)

T = TypeVar("T")


def supports(runner: CIRunner, method: str) -> bool:
    """Whether the runner answers `method` at all, without calling the CI."""
    return getattr(type(runner), method, None) is not getattr(CIRunner, method)


def optional(read: Callable[[], T]) -> Optional[T]:
    """What the CI answered, or None when it cannot answer or fails: the page shows the rest."""
    try:
        return read()
    except (NotImplementedError, ActionPlatformError):
        return None


def upstream(read: Callable[[], T]) -> T:
    try:
        return read()
    except NotImplementedError as e:
        raise NotFound(str(e)) from e
    except ActionPlatformError as e:
        raise Upstream(str(e)) from e


def capped(text: str, limit: int = MAX_LOG_BYTES) -> tuple[str, bool]:
    """At most `limit` bytes of `text`, its end kept: the newest lines are the ones a member follows."""
    data = text.encode("utf-8")

    if len(data) <= limit:
        return text, False

    tail = data[-limit:].decode("utf-8", "ignore")
    newline = tail.find("\n")

    if 0 <= newline < 4096:
        tail = tail[newline + 1 :]

    skipped = len(data) - len(tail.encode("utf-8"))

    return f"[{skipped} bytes skipped: download the log to read them]\n{tail}", True


def run_row(job: str, run: Run) -> schemas.CiPipelineRun:
    return schemas.CiPipelineRun(
        job=job,
        number=run.number,
        status=run.status,
        name=run.name,
        url=run.url,
        branch=run.branch,
        sha=run.sha,
        trigger=run.trigger,
        started_at=run.started_at,
        duration_ms=run.duration_ms,
    )


def started(row: schemas.CiPipelineRun) -> datetime:
    if row.started_at is None:
        return EPOCH

    if row.started_at.tzinfo is None:
        return row.started_at.replace(tzinfo=timezone.utc)

    return row.started_at


class Pipelines:
    def __init__(self, ci: CiService, context: AppContext) -> None:
        self.ci = ci
        self.context = context

    def runner(self, organization_id: str, app: App) -> CIRunner:
        try:
            return self.ci.runner_for(organization_id, app, self.context.repo_of(app))
        except ActionPlatformError as e:
            raise Upstream(str(e)) from e

    def jobs(
        self, organization_id: str, app: App, kind: Optional[str] = None
    ) -> list[schemas.CiJob]:
        """The app's CI job, then every job or workflow its deploy targets run on the same CI."""
        kind = kind or self.ci.kind_of(organization_id, app)

        if kind == "none":
            return []

        found = {
            app.ci_job or "": schemas.CiJob(
                name=app.ci_job or "", kind="ci", label="CI"
            )
        }

        try:
            targets = self.context.config_of(app).targets
        except ActionPlatformError:
            targets = []

        for spec in targets:
            name = spec.job or spec.workflow

            if spec.run_by != kind or not name:
                continue

            label = spec.name + (f" · {', '.join(spec.stages)}" if spec.stages else "")
            known = found.get(name)

            if known is None:
                found[name] = schemas.CiJob(name=name, kind="cd", label=label)
            elif known.kind == "cd":
                known.label = f"{known.label}, {label}"

        return list(found.values())

    def job_of(self, organization_id: str, app: App, job: str) -> schemas.CiJob:
        found = next(
            (j for j in self.jobs(organization_id, app) if j.name == job), None
        )

        if found is None:
            raise NotFound(f"{job or 'the CI job'} is not a pipeline of this app")

        return found

    def runs(
        self,
        organization_id: str,
        app: App,
        job: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> schemas.CiPipelines:
        kind = self.ci.kind_of(organization_id, app)
        jobs = self.jobs(organization_id, app, kind)

        if not jobs:
            return schemas.CiPipelines(kind=kind, jobs=[], runs=[])

        chosen = jobs if job is None else [self.job_of(organization_id, app, job)]
        runner = self.runner(organization_id, app)
        rows: list[schemas.CiPipelineRun] = []
        errors: list[schemas.CiJobError] = []

        for item in chosen:
            try:
                found = runner.runs(item.name, RUNS_PER_JOB)
            except (NotImplementedError, ActionPlatformError) as e:
                errors.append(schemas.CiJobError(job=item.name, error=str(e)))
                continue

            rows.extend(run_row(item.name, r) for r in found)

        if status:
            rows = [r for r in rows if r.status == status]

        rows.sort(key=lambda r: (started(r), r.number), reverse=True)

        return schemas.CiPipelines(
            kind=kind,
            jobs=jobs,
            runs=rows[: max(1, min(limit, MAX_RUNS))],
            errors=errors,
        )

    def run(
        self, organization_id: str, app: App, job: str, number: int
    ) -> schemas.CiRunDetail:
        item = self.job_of(organization_id, app, job)
        runner = self.runner(organization_id, app)
        run = upstream(lambda: runner.run(job, number))
        stages = optional(lambda: runner.stages(job, number))
        inputs = (
            optional(lambda: runner.pending_inputs(job, number))
            if run.status in LIVE
            else None
        )

        return schemas.CiRunDetail(
            run=run_row(job, run),
            job=item,
            parameters={k: redact(str(v)) for k, v in (run.params or {}).items()},
            causes=[
                f"{c.description} ({c.user})"
                if c.user and c.user not in c.description
                else c.description
                for c in run.causes
            ],
            changes=[
                schemas.CiChange(sha=c.sha, author=c.author, message=c.message)
                for c in run.changes
            ],
            stages=None
            if stages is None
            else [
                schemas.CiStage(
                    id=s.id,
                    name=s.name,
                    status=s.status,
                    started_at=s.started_at,
                    duration_ms=s.duration_ms,
                    parent_id=s.parent_id,
                )
                for s in stages
            ],
            pending_inputs=None
            if inputs is None
            else [schemas.CiPendingInput(id=i.id, message=i.message) for i in inputs],
            waiting=self.waiting(runner, job) if run.status == "queued" else None,
            supports=schemas.CiSupports(
                log=supports(runner, "log"),
                tests=supports(runner, "tests"),
                artifacts=supports(runner, "artifacts"),
            ),
        )

    def waiting(self, runner: CIRunner, job: str) -> Optional[str]:
        queue = optional(runner.queue) or []

        return next((q.why for q in queue if q.job == job and q.why), None)

    def log(
        self,
        organization_id: str,
        app: App,
        job: str,
        number: int,
        start: int = 0,
        node: Optional[str] = None,
    ) -> schemas.CiLogChunk:
        if start < 0:
            raise Invalid("start is an offset: 0 or more")

        self.job_of(organization_id, app, job)
        runner = self.runner(organization_id, app)
        chunk = upstream(lambda: runner.log(job, number, start, node or None))
        text, truncated = capped(chunk.text)

        return schemas.CiLogChunk(
            text=redact(text),
            next_start=chunk.next_start,
            more=chunk.more,
            truncated=truncated,
        )

    def log_download(
        self, organization_id: str, app: App, job: str, number: int
    ) -> Iterator[bytes]:
        """The whole console as it stands, read chunk by chunk and handed on as it arrives."""
        self.job_of(organization_id, app, job)
        runner = self.runner(organization_id, app)
        first = upstream(lambda: runner.log(job, number, 0, None))

        def chunks() -> Iterator[bytes]:
            chunk = first

            for _ in range(MAX_DOWNLOAD_READS):
                if chunk.text:
                    yield redact(chunk.text).encode("utf-8")

                if not chunk.more or not chunk.text:
                    return

                chunk = runner.log(job, number, chunk.next_start, None)

        return chunks()

    def tests(
        self, organization_id: str, app: App, job: str, number: int
    ) -> schemas.CiTests:
        self.job_of(organization_id, app, job)
        runner = self.runner(organization_id, app)
        report = upstream(lambda: runner.tests(job, number))

        if report is None:
            return schemas.CiTests(report=None)

        return schemas.CiTests(
            report=schemas.CiTestReport(
                total=report.total,
                passed=report.passed,
                failed=report.failed,
                skipped=report.skipped,
                failures=[
                    schemas.CiTestFailure(
                        name=f.name,
                        class_name=f.class_name,
                        message=redact(f.message),
                        stack=redact(capped(f.stack, MAX_STACK)[0]),
                    )
                    for f in report.failures[:MAX_FAILURES]
                ],
            )
        )

    def artifacts(
        self, organization_id: str, app: App, job: str, number: int
    ) -> schemas.CiArtifacts:
        self.job_of(organization_id, app, job)
        runner = self.runner(organization_id, app)

        return schemas.CiArtifacts(
            artifacts=[
                schemas.CiArtifact(path=a.path, size=a.size)
                for a in upstream(lambda: runner.artifacts(job, number))
            ]
        )

    def artifact(
        self, organization_id: str, app: App, job: str, number: int, path: str
    ) -> tuple[schemas.CiArtifact, Iterator[bytes]]:
        """One archived file, only when the run lists it, streamed from the CI."""
        self.job_of(organization_id, app, job)
        runner = self.runner(organization_id, app)
        listed = next(
            (
                a
                for a in upstream(lambda: runner.artifacts(job, number))
                if a.path == path
            ),
            None,
        )

        if listed is None:
            raise NotFound(f"run {number} archived no {path}")

        stream = upstream(lambda: iter(runner.artifact(job, number, path)))
        head = upstream(lambda: next(stream, b""))

        def content() -> Iterator[bytes]:
            if head:
                yield head

            yield from stream

        return schemas.CiArtifact(path=listed.path, size=listed.size), content()
