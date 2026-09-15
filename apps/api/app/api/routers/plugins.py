"""Plugins on the hosted platform: install from the index, switch on and off, restart, and each plugin's options."""

from fastapi import APIRouter

from app import schemas
from app.api.dependencies import CallerDep, OrgDep, PluginsDep, allowed

router = APIRouter(prefix="/api/v1/plugins", tags=["plugins"])


def queued(job) -> schemas.PluginQueued:
    return schemas.PluginQueued(job=job.id, poll=f"/api/v1/jobs/{job.id}")


@router.get("")
def plugins(org: OrgDep, caller: CallerDep, manager: PluginsDep) -> schemas.Plugins:
    return manager.catalog()


@router.post("/{slug}/install", status_code=202)
def install_plugin(
    slug: str, org: OrgDep, caller: CallerDep, manager: PluginsDep
) -> schemas.PluginQueued:
    allowed(caller, org, "org.manage")

    return queued(manager.enqueue_install(slug, caller.user.id))


@router.post("/{slug}/remove", status_code=202)
def remove_plugin(
    slug: str, org: OrgDep, caller: CallerDep, manager: PluginsDep
) -> schemas.PluginQueued:
    allowed(caller, org, "org.manage")

    return queued(manager.enqueue_remove(slug, caller.user.id))


@router.post("/{slug}/enable")
def enable_plugin(
    slug: str, org: OrgDep, caller: CallerDep, manager: PluginsDep
) -> schemas.Ok:
    allowed(caller, org, "org.manage")
    manager.enable(slug)

    return schemas.Ok()


@router.post("/{slug}/disable")
def disable_plugin(
    slug: str, org: OrgDep, caller: CallerDep, manager: PluginsDep
) -> schemas.Ok:
    allowed(caller, org, "org.manage")
    manager.disable(slug)

    return schemas.Ok()


@router.post("/restart", status_code=202)
def restart_platform(
    org: OrgDep, caller: CallerDep, manager: PluginsDep
) -> schemas.PluginQueued:
    """The worker restarts through its job; the API answers and leaves right after — the container's restart policy brings both back."""
    allowed(caller, org, "org.manage")
    job = manager.enqueue_restart(caller.user.id)
    manager.restart_api()

    return queued(job)


@router.get("/{slug}/options")
def plugin_options(
    slug: str, org: OrgDep, caller: CallerDep, manager: PluginsDep
) -> schemas.PluginOptions:
    allowed(caller, org, "org.manage")

    return schemas.PluginOptions(options=manager.options(slug).all())


@router.put("/{slug}/options")
def set_plugin_options(
    slug: str,
    body: schemas.PluginOptions,
    org: OrgDep,
    caller: CallerDep,
    manager: PluginsDep,
) -> schemas.PluginOptions:
    """Replaces the plugin's options with the body's; a key left out is deleted."""
    allowed(caller, org, "org.manage")
    store = manager.options(slug)

    for key in set(store.all()) - set(body.options):
        store.delete(key)

    for key, value in body.options.items():
        store.set(key, value)

    return schemas.PluginOptions(options=store.all())
