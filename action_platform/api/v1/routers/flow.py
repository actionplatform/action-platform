from typing import Optional

from fastapi import APIRouter, Depends

from action_platform.api import schemas
from action_platform.api.core.deps import get_flow
from action_platform.api.services.flow import FlowService

router = APIRouter(prefix="/apps", tags=["flow"])


@router.post("/{id}/branches", status_code=201)
def start_branch(
    id: str, body: schemas.StartBranchRequest, flow: FlowService = Depends(get_flow)
) -> schemas.BranchResult:
    return flow.start_branch(id, body)


@router.post("/{id}/checkout")
def checkout(
    id: str, body: schemas.CheckoutRequest, flow: FlowService = Depends(get_flow)
) -> dict:
    return flow.checkout(id, body.branch)


@router.get("/{id}/pull-request")
def propose_pull_request(
    id: str,
    base: Optional[str] = None,
    title: Optional[str] = None,
    flow: FlowService = Depends(get_flow),
) -> schemas.PullRequestProposal:
    return flow.propose_pr(id, base, title)


@router.post("/{id}/pull-request", status_code=201)
def open_pull_request(
    id: str, body: schemas.PullRequestRequest, flow: FlowService = Depends(get_flow)
) -> schemas.PullRequestResult:
    return flow.open_pr(id, body)
