from typing import Optional

from fastapi import APIRouter

from app.schemas import activity as schemas
from app.api.dependencies import (
    FlowDep,
)

router = APIRouter(prefix="/api/apps", tags=["flow"])


@router.post("/{id}/branches", status_code=201)
def start_branch(
    id: str,
    body: schemas.StartBranchRequest,
    flow: FlowDep,
) -> schemas.BranchResult:
    return flow.start_branch(id, body)


@router.get("/{id}/branches/plan")
def plan_branch(
    id: str,
    kind: str,
    flow: FlowDep,
    code: str = "",
    slug: Optional[str] = None,
) -> schemas.BranchResult:
    return flow.plan_branch(id, kind, code, slug)


@router.post("/{id}/checkout")
def checkout(
    id: str,
    body: schemas.CheckoutRequest,
    flow: FlowDep,
) -> dict:
    return flow.checkout(id, body.branch)


@router.get("/{id}/pull-request")
def propose_pull_request(
    id: str,
    flow: FlowDep,
    base: Optional[str] = None,
    title: Optional[str] = None,
) -> schemas.PullRequestProposal:
    return flow.propose_pr(id, base, title)


@router.post("/{id}/pull-request", status_code=201)
def open_pull_request(
    id: str,
    body: schemas.PullRequestRequest,
    flow: FlowDep,
) -> schemas.PullRequestResult:
    return flow.open_pr(id, body)
