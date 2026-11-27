"""The CI of an app inside a project: which runner it reads, the runs imported from it, and its pipelines read live — runs, stages, logs, tests and artifacts — for any member who can read the app."""

import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.core.errors import Invalid

from action_platform.core.exception import ActionPlatformError
from app.api.dependencies import (
    CallerDep,
    CiDep,
    IntegrationsDep,
    OrgDep,
    PipelinesDep,
    ProjectsRepoDep,
    allowed,
    app_of,
    project_of,
)
from app.schemas import ci as schemas

router = APIRouter(prefix="/api/v1", tags=["management"])

UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def attachment(name: str) -> dict[str, str]:
    safe = UNSAFE.sub("-", name).strip("-.") or "download"

    return {
        "content-disposition": f'attachment; filename="{safe}"',
        "cache-control": "no-store",
    }


@router.get("/projects/{project_id}/apps/{app_id}/ci")
def ci_runs(
    project_id: str,
    app_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    ci: CiDep,
    page: int = 1,
    per: int = 10,
) -> schemas.CiRuns:
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    return ci.page(org.id, app, page, per)


@router.put("/projects/{project_id}/apps/{app_id}/ci")
def link_ci(
    project_id: str,
    app_id: str,
    body: schemas.CiLinkRequest,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    ci: CiDep,
    integrations: IntegrationsDep,
) -> schemas.CiLink:
    allowed(caller, org, "app.configure", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    if body.ci_host_id and integrations.ci_host(org.id, body.ci_host_id) is None:
        raise HTTPException(404, "ci host not found")

    writes.set_app_ci(app, body.ci_host_id or None, body.job)

    return ci.link(org.id, app)


@router.post("/projects/{project_id}/apps/{app_id}/ci/sync")
def sync_ci(
    project_id: str,
    app_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    ci: CiDep,
    page: int = 1,
    per: int = 10,
) -> schemas.CiRuns:
    allowed(caller, org, "app.sync", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    try:
        ci.sync(org.id, app)
        error = None
    except ActionPlatformError as e:
        error = str(e)

    return ci.page(org.id, app, page, per, error)


@router.post("/projects/{project_id}/apps/{app_id}/ci/run", status_code=202)
def start_ci(
    project_id: str,
    app_id: str,
    body: schemas.CiStartRequest,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    ci: CiDep,
) -> schemas.CiStarted:
    allowed(caller, org, "app.flow", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    if not body.ref.strip():
        raise Invalid("a run starts on a branch or tag: ref is required")

    try:
        return schemas.CiStarted(**ci.start(org.id, app, body.ref.strip()))
    except ActionPlatformError as e:
        raise Invalid(str(e)) from e


@router.get("/projects/{project_id}/apps/{app_id}/ci/runs")
def pipeline_runs(
    project_id: str,
    app_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    pipelines: PipelinesDep,
    job: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> schemas.CiPipelines:
    app = app_of(writes, caller, project_of(writes, org, project_id), app_id)

    return pipelines.runs(org.id, app, job, status or None, limit)


@router.get("/projects/{project_id}/apps/{app_id}/ci/deploy-runs")
def deploy_runs(
    project_id: str,
    app_id: str,
    version: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    pipelines: PipelinesDep,
    stage: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    url: list[str] = Query(default=[]),
) -> schemas.CiDeployRuns:
    app = app_of(writes, caller, project_of(writes, org, project_id), app_id)

    return pipelines.deploy_runs(org.id, app, stage, version, since, until, url)


@router.get("/projects/{project_id}/apps/{app_id}/ci/runs/{number}")
def pipeline_run(
    project_id: str,
    app_id: str,
    number: int,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    pipelines: PipelinesDep,
    job: str = "",
) -> schemas.CiRunDetail:
    app = app_of(writes, caller, project_of(writes, org, project_id), app_id)

    return pipelines.run(org.id, app, job, number)


@router.get("/projects/{project_id}/apps/{app_id}/ci/runs/{number}/log")
def pipeline_log(
    project_id: str,
    app_id: str,
    number: int,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    pipelines: PipelinesDep,
    job: str = "",
    start: int = 0,
    node: Optional[str] = None,
) -> schemas.CiLogChunk:
    app = app_of(writes, caller, project_of(writes, org, project_id), app_id)

    return pipelines.log(org.id, app, job, number, start, node)


@router.get(
    "/projects/{project_id}/apps/{app_id}/ci/runs/{number}/log/download",
    response_class=StreamingResponse,
)
def pipeline_log_download(
    project_id: str,
    app_id: str,
    number: int,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    pipelines: PipelinesDep,
    job: str = "",
) -> StreamingResponse:
    app = app_of(writes, caller, project_of(writes, org, project_id), app_id)
    body = pipelines.log_download(org.id, app, job, number)

    return StreamingResponse(
        body,
        media_type="text/plain; charset=utf-8",
        headers=attachment(f"{job or app.name}-{number}.log"),
    )


@router.get("/projects/{project_id}/apps/{app_id}/ci/runs/{number}/tests")
def pipeline_tests(
    project_id: str,
    app_id: str,
    number: int,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    pipelines: PipelinesDep,
    job: str = "",
) -> schemas.CiTests:
    app = app_of(writes, caller, project_of(writes, org, project_id), app_id)

    return pipelines.tests(org.id, app, job, number)


@router.get("/projects/{project_id}/apps/{app_id}/ci/runs/{number}/artifacts")
def pipeline_artifacts(
    project_id: str,
    app_id: str,
    number: int,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    pipelines: PipelinesDep,
    job: str = "",
) -> schemas.CiArtifacts:
    app = app_of(writes, caller, project_of(writes, org, project_id), app_id)

    return pipelines.artifacts(org.id, app, job, number)


@router.get(
    "/projects/{project_id}/apps/{app_id}/ci/runs/{number}/artifacts/download",
    response_class=StreamingResponse,
)
def pipeline_artifact(
    project_id: str,
    app_id: str,
    number: int,
    path: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    pipelines: PipelinesDep,
    job: str = "",
) -> StreamingResponse:
    app = app_of(writes, caller, project_of(writes, org, project_id), app_id)
    listed, body = pipelines.artifact(org.id, app, job, number, path)
    return StreamingResponse(
        body,
        media_type="application/octet-stream",
        headers=attachment(listed.path.rsplit("/", 1)[-1]),
    )
