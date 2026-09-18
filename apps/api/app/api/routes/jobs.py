"""Jobs the API queued for the worker."""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.dependencies import (
    CallerDep,
    ProjectsRepoDep,
    QueueDep,
)
from app.core.db.models.auth import User
from app.core.shared import people
from app.schemas.common import page_bounds
from app.services.jobs import JobQueue

router = APIRouter(prefix="/api/v1", tags=["management"])


class JobOut(BaseModel):
    id: str
    kind: str
    status: str
    app_id: Optional[str] = None
    attempts: int
    stage: Optional[str] = None
    dry_run: Optional[bool] = None
    version: Optional[str] = None
    by: Optional[str] = None
    started_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    finished_at: Optional[datetime] = None


class JobPage(BaseModel):
    items: list[JobOut]
    total: int
    page: int
    per: int


@router.get("/jobs/page")
def jobs_page(
    app: str,
    caller: CallerDep,
    directory: ProjectsRepoDep,
    queue: QueueDep,
    kinds: str = "deploy,destroy",
    page: int = 1,
    per: int = 10,
) -> JobPage:
    found = directory.app_by_registry_id(app)

    if (
        found is None
        or caller.member_of(found[1].organization_id) is None
        or not caller.within_reach(found[0].id, found[1].id)
    ):
        raise HTTPException(404, "app not found")

    wanted = [k.strip() for k in kinds.split(",") if k.strip()]
    page, per, offset = page_bounds(page, per)

    return JobPage(
        items=[
            _out(directory, JobQueue.view(j))
            for j in queue.for_app(found[0].id, limit=per, kinds=wanted, offset=offset)
        ],
        total=queue.count_for_app(found[0].id, kinds=wanted),
        page=page,
        per=per,
    )


@router.get("/jobs/{id}")
def job(
    id: str,
    caller: CallerDep,
    directory: ProjectsRepoDep,
    queue: QueueDep,
) -> JobOut:
    found = queue.get(id)

    if found is None or (
        found.organization_id and caller.member_of(found.organization_id) is None
    ):
        raise HTTPException(404, "no such job")

    return _out(directory, JobQueue.view(found))


def _out(directory: ProjectsRepoDep, view: dict) -> JobOut:
    user_id = view.pop("user_id", None)
    user = directory.db.get(User, user_id) if user_id else None

    return JobOut(**view, by=people.label(user))


@router.get("/jobs")
def jobs(
    app: str,
    caller: CallerDep,
    directory: ProjectsRepoDep,
    queue: QueueDep,
    kind: Optional[str] = None,
    limit: int = 20,
) -> list[JobOut]:
    found = directory.app_by_registry_id(app)

    if (
        found is None
        or caller.member_of(found[1].organization_id) is None
        or not caller.within_reach(found[0].id, found[1].id)
    ):
        raise HTTPException(404, "app not found")

    return [
        _out(directory, JobQueue.view(j))
        for j in queue.for_app(found[0].id, limit=max(1, min(limit, 500)), kind=kind)
    ]
