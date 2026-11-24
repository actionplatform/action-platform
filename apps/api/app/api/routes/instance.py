"""Instance health: an open probe for monitors, and the owner's view with a test email."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from action_platform.core.exception import ProviderError
from app.api.dependencies import (
    CallerDep,
    IntegrationsDep,
    OrgDep,
    allowed,
)
from app.schemas import instance as schemas
from app.services.instance import InstanceHealth, probe_mail
from app.services.templates import CatalogService

router = APIRouter(tags=["instance"])


@router.get("/api/health", response_model=schemas.Health)
def health(request: Request) -> JSONResponse:
    """200 when the database answers, migrations are at head and a worker takes each kind group; 503 with the same body otherwise."""
    probe = InstanceHealth(request.app.state.db).probe()

    return JSONResponse(probe, status_code=200 if probe["status"] == "ok" else 503)


def owner(caller, org) -> None:
    allowed(caller, org, "org.manage")

    if caller.role_in(org.id) != "owner":
        raise HTTPException(403, "only an owner may see the instance")


@router.get("/api/v1/instance/health")
def instance_health(
    request: Request,
    caller: CallerDep,
    org: OrgDep,
    writes: IntegrationsDep,
) -> schemas.InstanceHealthOut:
    owner(caller, org)
    state = request.app.state
    service = InstanceHealth(state.db)
    last = state.mail_log.last

    return schemas.InstanceHealthOut(
        **service.probe(),
        **service.detail(),
        **CatalogService().version(),
        integrations=schemas.Integrations(
            smtp=schemas.SmtpOut(
                **service.smtp(state.mailer),
                last_failure=(
                    schemas.MailFailureOut(at=last.at, what=last.what, error=last.error)
                    if last
                    else None
                ),
            ),
            google=schemas.GoogleOut(
                **service.google(state.google is not None, state.public_url)
            ),
            sentry_api=service.sentry(),
            oauth_apps=[
                schemas.OAuthAppState(provider=p, configured=a is not None)
                for p, a in writes.oauth_apps().items()
            ],
        ),
    )


@router.post("/api/v1/instance/test-email")
def send_test_email(
    request: Request,
    caller: CallerDep,
    org: OrgDep,
) -> schemas.TestEmailOut:
    owner(caller, org)
    mailer = request.app.state.mailer
    to = caller.user.email

    if mailer is None:
        return schemas.TestEmailOut(
            sent=False, to=to, error="email is not configured: set AP_SMTP_HOST"
        )

    try:
        mailer.send(probe_mail(caller.user))
    except ProviderError as e:
        request.app.state.mail_log.failed("test email", str(e))

        return schemas.TestEmailOut(sent=False, to=to, error=str(e))

    request.app.state.mail_log.sent()

    return schemas.TestEmailOut(sent=True, to=to)
