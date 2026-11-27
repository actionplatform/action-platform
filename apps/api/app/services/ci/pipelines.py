"""An app's pipelines read live from its CI: the jobs it names, their runs, and one run's stages, log, tests and artifacts — passed through to the member, never stored."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable, Iterator, Optional, TypeVar

from action_platform.abc.ci_runner import CIRunner, LogChunk
from action_platform.core.context import Run
from action_platform.core.exception import ActionPlatformError
from app.core.db.models import App
from app.core.errors import Invalid, NotFound, Upstream
from app.schemas import ci as schemas
from action_platform.core.redact import redact
from app.services.ci.service import CiService
from app.services.workspace.app_context import AppContext

MAX_LOG_BYTES = 256 * 1024
DOWNLOAD_WINDOW = 1024 * 1024
MAX_PENDING_LINE = 64 * 1024
RUNS_PER_JOB = 25
MAX_RUNS = 100
MAX_FAILURES = 200
MAX_STACK = 16 * 1024
LIVE = ("queued", "running")
EPOCH = datetime.min.replace(tzinfo=timezone.utc)
SLACK = timedelta(minutes=2)

T = TypeVar("T")


def supports(runner: CIRunner, method: str) -> bool:
    """Whether the runner answers `method` at all, without calling the CI."""
    own = getattr(type(runner), method, None)

    return callable(own) and own is not getattr(CIRunner, method, None)


def text_of(piece: str | bytes) -> str:
    return piece.decode("utf-8", "replace") if isinstance(piece, bytes) else piece


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


def read_log(
    runner: CIRunner,
    job: str,
    number: int,
    start: int,
    node: Optional[str],
    limit: int,
) -> LogChunk:
    return runner.log(job, number, start, node, limit)


def masked_lines(chunks: Iterable[str]) -> Iterator[bytes]:
    """Chunks re-cut on line ends, so a secret split across two reads is still masked; a line longer than the bound is let through as it is."""
    pending = ""

    for text in chunks:
        pending += text
        cut = pending.rfind("\n")

        if cut == -1 and len(pending) < MAX_PENDING_LINE:
            continue

        head, pending = (
            (pending[: cut + 1], pending[cut + 1 :]) if cut != -1 else (pending, "")
        )
        yield redact(head).encode("utf-8")

    if pending:
        yield redact(pending).encode("utf-8")


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


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def started(row: schemas.CiPipelineRun) -> datetime:
    return EPOCH if row.started_at is None else utc(row.started_at)


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

    def deploy_runs(
        self,
        organization_id: str,
        app: App,
        stage: Optional[str],
        version: str,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        urls: Optional[list[str]] = None,
    ) -> schemas.CiDeployRuns:
        """The run each CI-run target of `stage` made for one deploy of `version`: the run a result links to, else the one that shipped that version within the deploy's time."""
        kind = self.ci.kind_of(organization_id, app)
        version = version.lstrip("v")
        links = set(urls or [])

        try:
            targets = self.context.config_of(app).targets
        except ActionPlatformError:
            targets = []

        specs = [
            s
            for s in targets
            if s.run_by == kind
            and not s.platform
            and (s.job or s.workflow)
            and (not stage or s.serves(stage))
        ]

        if kind == "none" or not specs:
            return schemas.CiDeployRuns(runs=[])

        runner = self.runner(organization_id, app)
        low = utc(since) - SLACK if since else None
        high = utc(until) + SLACK if until else None
        found: list[schemas.CiDeployRun] = []

        for spec in specs:
            job = spec.job or spec.workflow

            try:
                runs = runner.runs(job, RUNS_PER_JOB)
            except (NotImplementedError, ActionPlatformError):
                continue

            def ships(run: Run, spec=spec) -> bool:
                if spec.run_version(run.branch, run.params) != version:
                    return False

                ran = spec.run_stage(run.params)

                if stage and ran and ran != stage:
                    return False

                at = utc(run.started_at) if run.started_at else None

                return at is None or (
                    (low is None or at >= low) and (high is None or at <= high)
                )

            match = next((r for r in runs if r.url and r.url in links), None)

            if match is None:
                candidates = sorted(
                    (r for r in runs if ships(r)),
                    key=lambda r: (utc(r.started_at) if r.started_at else EPOCH),
                )
                match = candidates[0] if candidates else None

            if match is not None:
                found.append(
                    schemas.CiDeployRun(target=spec.name, run=run_row(job, match))
                )

        return schemas.CiDeployRuns(runs=found)

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
        chunk = upstream(
            lambda: read_log(runner, job, number, start, node or None, MAX_LOG_BYTES)
        )
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
        """The whole console as it stands, read window by window through the runner's `log_stream` and handed on as each arrives — never held whole."""
        self.job_of(organization_id, app, job)
        runner = self.runner(organization_id, app)

        stream = upstream(
            lambda: iter(runner.log_stream(job, number, 0, None, DOWNLOAD_WINDOW))
        )
        first = upstream(lambda: next(stream, None))

        def texts() -> Iterator[str]:
            if first is None:
                return

            yield text_of(first.text)

            for chunk in stream:
                yield text_of(chunk.text)

        return masked_lines(texts())

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
