"""Jobs the API queued for the worker."""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import (
    get_caller,
    get_directory,
    get_queue,
)
from app.services.access.caller import Caller
from app.services.directory import DirectoryService
from app.services.jobs import JobQueue


router = APIRouter(prefix="/api/v1", tags=["management"])


class JobOut(BaseModel):
    id: str
    kind: str
    status: str
    app_id: Optional[str] = None
    attempts: int
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    finished_at: Optional[datetime] = None


@router.get("/jobs/{id}")
def job(
    id: str, caller: Caller = Depends(get_caller), queue: JobQueue = Depends(get_queue)
) -> JobOut:
    found = queue.get(id)

    if found is None or (
        found.organization_id and caller.member_of(found.organization_id) is None
    ):
        raise HTTPException(404, "no such job")

    return JobOut(**JobQueue.view(found))


@router.get("/jobs")
def jobs(
    app: str,
    caller: Caller = Depends(get_caller),
    directory: DirectoryService = Depends(get_directory),
    queue: JobQueue = Depends(get_queue),
) -> list[JobOut]:
    found = directory.app_by_registry_id(app)

    if (
        found is None
        or caller.member_of(found[1].organization_id) is None
        or not caller.within_reach(found[0].id, found[1].id)
    ):
        raise HTTPException(404, "app not found")

    return [JobOut(**JobQueue.view(j)) for j in queue.for_app(found[0].id)]
