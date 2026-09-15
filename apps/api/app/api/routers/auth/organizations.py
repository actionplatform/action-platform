"""Organizations and their members, created by the web app on setup."""

from fastapi import APIRouter, Depends

from app.core.auth.service import (
    AuthService,
)
from app.api.dependencies import get_auth
from app.core.db.models import (
    Session,
)
from app.schemas import auth as schemas


from app.api.routers.auth.support import (
    current_session,
    organization_out,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/organizations", status_code=201)
def create_organization(
    body: schemas.CreateOrganizationRequest,
    session: Session = Depends(current_session),
    auth: AuthService = Depends(get_auth),
) -> schemas.OrganizationOut:
    return organization_out(
        auth.create_organization(
            session, body.name, body.slug, body.git_author_name, body.git_author_email
        )
    )


@router.post("/members", status_code=201)
def add_member(
    body: schemas.AddMemberRequest,
    session: Session = Depends(current_session),
    auth: AuthService = Depends(get_auth),
) -> schemas.MemberAdded:
    user, existed = auth.add_member_account(
        session, body.organization_id, body.name, body.email, body.password, body.role
    )

    return schemas.MemberAdded(user_id=user.id, existed=existed)
