"""Who is calling and which organization the request is about."""

from typing import Optional

from fastapi import HTTPException, Request

from app.core.db.models import Organization
from app.services.access.caller import Caller

MANAGE = {
    "projects": "project.manage",
    "projects/team": "project.manage",
    "teams": "org.manage",
    "teams/members": "org.manage",
    "members/role": "org.manage",
}


def get_caller(request: Request) -> Caller:
    caller = getattr(request.state, "caller", None)

    if caller is None:
        raise HTTPException(401, "unauthorized")

    return caller


def requested_org(
    caller: Caller, x_organization: Optional[str], organization: Optional[str]
) -> Optional[Organization]:
    wanted = (x_organization or organization or "").strip()

    if wanted and (caller.all_organizations or caller.scope is None):
        found = caller.member_of(wanted)

        if found is not None:
            return found

    return caller.organization


def required_org(
    caller: Caller, x_organization: Optional[str], organization: Optional[str]
) -> Organization:
    org = requested_org(caller, x_organization, organization)

    if org is None:
        raise HTTPException(
            400,
            "this token spans every organization: send X-Organization: <id or slug>",
        )

    return org


def org_of(caller: Caller, x_organization: Optional[str]) -> Organization:
    return required_org(caller, x_organization, None)


def allowed(
    caller: Caller, org: Organization, permission: str, whole_org: bool = True
) -> None:
    ok, why = caller.allows(org.id, permission)

    if not ok:
        raise HTTPException(403, why)

    if whole_org and (caller.project_id or caller.app_id):
        raise HTTPException(
            403, "a token limited to a project or app cannot manage the organization"
        )


def manageable(caller: Caller, org: Organization, path: str) -> None:
    permission = MANAGE[path]
    ok, why = caller.allows(org.id, permission)

    if not ok:
        raise HTTPException(403, why)

    if caller.project_id or caller.app_id:
        raise HTTPException(
            403, "a token limited to a project or app cannot manage the organization"
        )
