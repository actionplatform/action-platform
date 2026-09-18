"""Deliveries from the code host, and the URL and secret each host signs them with."""

from fastapi import APIRouter, Request

from action_platform.settings import settings
from app.api.dependencies import (
    CallerDep,
    DbDep,
    IntegrationsDep,
    OrgDep,
    QueueDep,
    allowed,
)
from app.repositories.workspace.source import get_registry
from app.schemas import integrations as schemas
from app.services.integrations.webhooks import Webhooks

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.post("/webhooks/{host_id}", status_code=202)
async def receive(
    host_id: str, request: Request, db: DbDep, queue: QueueDep
) -> schemas.WebhookReceived:
    """The code host calls this; the signature or token in the headers is the only credential."""
    body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}
    result = Webhooks(db, request.app.state.sealer, get_registry(), queue).receive(
        host_id, headers, body
    )

    return schemas.WebhookReceived(**result)


@router.get("/hosts/{host_id}/webhook")
def webhook(
    host_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: IntegrationsDep,
) -> schemas.WebhookInfo:
    allowed(caller, org, "org.manage")
    host = writes.host(org.id, host_id)

    return schemas.WebhookInfo(
        url=f"{settings.PUBLIC_URL.rstrip('/')}/api/webhooks/{host_id}",
        configured=bool(host and host.webhook_secret_encrypted),
        kind=host.kind if host else "",
    )


@router.post("/hosts/{host_id}/webhook")
def rotate_webhook(
    host_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: IntegrationsDep,
) -> schemas.WebhookSecret:
    """A new secret; the old one stops verifying at once. Shown this once."""
    allowed(caller, org, "org.manage")
    secret = writes.rotate_webhook_secret(org.id, host_id)
    host = writes.host(org.id, host_id)

    return schemas.WebhookSecret(
        url=f"{settings.PUBLIC_URL.rstrip('/')}/api/webhooks/{host_id}",
        secret=secret,
        kind=host.kind if host else "",
    )
