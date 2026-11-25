"""Git-flow on the code host: what an app's host enforces, the per-app setting, applying it now, and the organization's default."""

from fastapi import APIRouter

from app.api.dependencies import (
    CallerDep,
    OrgDep,
    ProjectsRepoDep,
    ProtectionDep,
    QueueDep,
    allowed,
    app_of,
    project_of,
)
from app.schemas import protection as schemas
from app.services.protection.sweep import RECONCILE, SWEEP, reconcile_payload

router = APIRouter(prefix="/api/v1", tags=["management"])


def _actor(caller: CallerDep) -> str:
    return caller.user.name or caller.user.email


@router.get("/projects/{project_id}/apps/{app_id}/protection")
def protection_status(
    project_id: str,
    app_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    protection: ProtectionDep,
    refresh: bool = False,
) -> schemas.Protection:
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    if refresh:
        protection.check(org.id, app)

    return schemas.Protection(**protection.view(org.id, app))


@router.put("/projects/{project_id}/apps/{app_id}/protection")
def set_protection(
    project_id: str,
    app_id: str,
    body: schemas.ProtectionRequest,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    protection: ProtectionDep,
    queue: QueueDep,
) -> schemas.Protection:
    allowed(caller, org, "app.configure", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)
    view = protection.set_enforce(org.id, app, body.enforce, _actor(caller))
    protection.db.commit()
    job_id = None

    if view["enforce"]:
        job_id = queue.enqueue(
            RECONCILE,
            {
                **reconcile_payload(org.id, app.id, app.registry_id, "apply"),
                "actor": _actor(caller),
            },
            organization_id=org.id,
            app_id=app.id,
            dedupe_key="apply",
        ).id

    return schemas.Protection(**view, job_id=job_id)


@router.post("/projects/{project_id}/apps/{app_id}/protection/apply")
def apply_protection(
    project_id: str,
    app_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    protection: ProtectionDep,
) -> schemas.Protection:
    allowed(caller, org, "app.configure", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)
    protection.apply(org.id, app, _actor(caller))

    return schemas.Protection(**protection.view(org.id, app))


@router.get("/settings/protection")
def protection_default(
    org: OrgDep, caller: CallerDep, protection: ProtectionDep
) -> schemas.ProtectionDefault:
    return schemas.ProtectionDefault(enforce=protection.store.default(org.id))


@router.put("/settings/protection")
def set_protection_default(
    body: schemas.ProtectionDefault,
    org: OrgDep,
    caller: CallerDep,
    protection: ProtectionDep,
    queue: QueueDep,
) -> schemas.ProtectionDefault:
    allowed(caller, org, "org.manage")
    protection.set_default(org.id, body.enforce)
    protection.db.commit()

    if body.enforce:
        queue.enqueue(SWEEP, {})

    return schemas.ProtectionDefault(enforce=body.enforce)
