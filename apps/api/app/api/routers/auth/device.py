"""The device flow: a CLI or MCP asks for a code, the browser approves it, the token follows."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import (
    AuthDep,
)
from app.api.routers.auth.support import (
    current_session,
    device_request_out,
    grant_of,
    limited,
)
from app.core.auth.service import (
    DEVICE_TTL,
    SESSION_TTL,
)
from app.core.db.models import (
    Session,
)
from app.schemas import auth as schemas

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/device/code", dependencies=[Depends(limited("device-code"))])
def device_code(
    body: schemas.DeviceCodeRequest,
    auth: AuthDep,
) -> schemas.DeviceCodeOut:
    code = auth.device_code(body.client_id, body.scope)

    return schemas.DeviceCodeOut(
        device_code=code.device_code,
        user_code=code.user_code,
        verification_uri=auth.verification_uri,
        verification_uri_complete=f"{auth.verification_uri}?user_code={code.user_code}",
        expires_in=int(DEVICE_TTL.total_seconds()),
        interval=code.polling_interval or 0,
    )


@router.post("/device/token", dependencies=[Depends(limited("device-token"))])
def device_token(
    body: schemas.DeviceTokenRequest,
    auth: AuthDep,
) -> schemas.DeviceTokenOut:
    if body.grant_type != "urn:ietf:params:oauth:grant-type:device_code":
        raise HTTPException(400, "unsupported grant_type")

    session, scope = auth.device_token(body.device_code, body.client_id)

    return schemas.DeviceTokenOut(
        access_token=session.token,
        scope=scope,
        expires_in=int(SESSION_TTL.total_seconds()),
    )


@router.get("/device")
def device_request(
    user_code: str,
    auth: AuthDep,
    session: Session = Depends(current_session),
) -> schemas.DeviceRequestOut:
    code = auth.device_request(user_code)

    if code is None:
        raise HTTPException(404, "invalid code")

    return device_request_out(auth, code)


@router.post("/device/approve")
def device_approve(
    body: schemas.DeviceDecision,
    auth: AuthDep,
    session: Session = Depends(current_session),
) -> schemas.DeviceDecisionOut:
    if body.grant is not None:
        auth.device_grant(session, body.user_code, grant_of(body.grant))

    return schemas.DeviceDecisionOut(
        status=auth.device_approve(session, body.user_code).status
    )


@router.post("/device/deny")
def device_deny(
    body: schemas.DeviceDecision,
    auth: AuthDep,
    session: Session = Depends(current_session),
) -> schemas.DeviceDecisionOut:
    return schemas.DeviceDecisionOut(
        status=auth.device_deny(session, body.user_code).status
    )
