"""Organizations and their members, created by the web app on setup."""

from fastapi import APIRouter, Depends

from app.api.dependencies import (
    AuthDep,
)
from app.api.routers.auth.support import (
    current_session,
    organization_out,
)
from app.core.db.models import (
    Session,
)
from app.schemas import auth as schemas

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/organizations", status_code=201)
def create_organization(
    body: schemas.CreateOrganizationRequest,
    auth: AuthDep,
    session: Session = Depends(current_session),
) -> schemas.OrganizationOut:
    return organization_out(
        auth.create_organization(
            session, body.name, body.slug, body.git_author_name, body.git_author_email
        )
    )


@router.post("/members", status_code=201)
def add_member(
    body: schemas.AddMemberRequest,
    auth: AuthDep,
    session: Session = Depends(current_session),
) -> schemas.MemberAdded:
    user, existed = auth.add_member_account(
        session, body.organization_id, body.name, body.email, body.password, body.role
    )

    return schemas.MemberAdded(user_id=user.id, existed=existed)
