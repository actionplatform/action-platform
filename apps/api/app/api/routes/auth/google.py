"""Sign in with Google: the web app starts the round trip here and hands back what Google returned."""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import AuthDep
from app.api.routes.auth.support import limited, signed
from app.schemas import auth as schemas
from app.services.auth.google import GoogleClient

router = APIRouter(prefix="/api/auth/google", tags=["auth"])


def google_client(request: Request) -> GoogleClient:
    config = request.app.state.google

    if config is None or request.app.state.secrets is None:
        raise HTTPException(
            404,
            "Google sign-in is not configured: set AP_GOOGLE_CLIENT_ID and AP_GOOGLE_CLIENT_SECRET",
        )

    return GoogleClient(config, request.app.state.secrets)


@router.post("/start", dependencies=[Depends(limited("google"))])
def start(
    body: schemas.GoogleStartRequest,
    google: GoogleClient = Depends(google_client),
) -> schemas.GoogleStartOut:
    begun = google.start(body.origin, body.next)

    return schemas.GoogleStartOut(url=begun.url, verifier=begun.verifier)


@router.post("/callback", dependencies=[Depends(limited("google"))])
def callback(
    body: schemas.GoogleCallbackRequest,
    auth: AuthDep,
    google: GoogleClient = Depends(google_client),
) -> schemas.GoogleSigned:
    profile, next_path = google.finish(
        body.origin, body.code, body.state, body.verifier
    )
    user, session = auth.sign_in_with_google(profile, body.ip_address, body.user_agent)
    invitation = auth.pending_invitation_of(user.email)
    out = signed(auth, user, session)

    return schemas.GoogleSigned(
        user=out.user,
        session=out.session,
        next=f"/invite/{invitation}" if invitation else next_path,
    )
