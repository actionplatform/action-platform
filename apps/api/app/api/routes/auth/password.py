"""Password recovery: ask for a reset link by email, then set a new password with it."""

import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from action_platform.core.exception import ProviderError
from app.api.dependencies import AuthDep
from app.api.routes.auth.support import limited
from app.schemas import auth as schemas
from app.services.auth.recovery import reset_mail

log = logging.getLogger("action_platform.api")

router = APIRouter(prefix="/api/auth/password", tags=["auth"])


@router.post(
    "/forgot", status_code=202, dependencies=[Depends(limited("password-forgot"))]
)
def forgot(
    body: schemas.ForgotPasswordRequest,
    request: Request,
    auth: AuthDep,
) -> Response:
    mailer = request.app.state.mailer

    if mailer is None:
        raise HTTPException(503, "email is not configured: set AP_SMTP_HOST")

    found = auth.request_password_reset(body.email)

    if found is not None:
        user, token = found
        link = f"{request.app.state.public_url}/reset-password?{urlencode({'token': token})}"

        try:
            mailer.send(reset_mail(user, link))
        except ProviderError:
            log.exception("password reset email to user %s not sent", user.id)

    return Response(status_code=202)


@router.post(
    "/reset", status_code=204, dependencies=[Depends(limited("password-reset"))]
)
def reset(
    body: schemas.ResetPasswordRequest,
    auth: AuthDep,
) -> Response:
    auth.reset_password(body.token, body.password)

    return Response(status_code=204)
