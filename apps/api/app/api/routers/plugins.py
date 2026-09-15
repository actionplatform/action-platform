"""Plugins on the hosted platform. Installing, switching and restarting change the whole platform — platform admins only; a plugin's options belong to the caller's organization."""

from fastapi import APIRouter

from app.schemas.catalog import Plugins
from app.schemas.common import Ok
from app.schemas.plugins import PluginOptions, PluginQueued
from app.api.dependencies import CallerDep, OrgDep, PluginsDep, allowed, platform_admin

router = APIRouter(prefix="/api/v1/plugins", tags=["plugins"])


def queued(job) -> PluginQueued:
    return PluginQueued(job=job.id, poll=f"/api/v1/jobs/{job.id}")


@router.get("")
def plugins(org: OrgDep, caller: CallerDep, manager: PluginsDep) -> Plugins:
    return manager.catalog()


@router.post("/{slug}/install", status_code=202)
def install_plugin(
    slug: str, org: OrgDep, caller: CallerDep, manager: PluginsDep
) -> PluginQueued:
    platform_admin(caller)

    return queued(manager.enqueue_install(slug, caller.user.id))


@router.post("/{slug}/remove", status_code=202)
def remove_plugin(
    slug: str, org: OrgDep, caller: CallerDep, manager: PluginsDep
) -> PluginQueued:
    platform_admin(caller)

    return queued(manager.enqueue_remove(slug, caller.user.id))


@router.post("/{slug}/enable")
def enable_plugin(slug: str, org: OrgDep, caller: CallerDep, manager: PluginsDep) -> Ok:
    platform_admin(caller)
    manager.enable(slug)

    return Ok()


@router.post("/{slug}/disable")
def disable_plugin(
    slug: str, org: OrgDep, caller: CallerDep, manager: PluginsDep
) -> Ok:
    platform_admin(caller)
    manager.disable(slug)

    return Ok()


@router.post("/restart", status_code=202)
def restart_platform(
    org: OrgDep, caller: CallerDep, manager: PluginsDep
) -> PluginQueued:
    """The worker restarts through its job; the API answers and leaves right after — the container's restart policy brings both back."""
    platform_admin(caller)
    job = manager.enqueue_restart(caller.user.id)
    manager.restart_api()

    return queued(job)


@router.get("/{slug}/options")
def plugin_options(
    slug: str, org: OrgDep, caller: CallerDep, manager: PluginsDep
) -> PluginOptions:
    allowed(caller, org, "org.manage")

    return PluginOptions(options=manager.options(slug, org.id).all())


@router.put("/{slug}/options")
def set_plugin_options(
    slug: str,
    body: PluginOptions,
    org: OrgDep,
    caller: CallerDep,
    manager: PluginsDep,
) -> PluginOptions:
    """Replaces the plugin's options with the body's; a key left out is deleted."""
    allowed(caller, org, "org.manage")
    store = manager.options(slug, org.id)

    for key in set(store.all()) - set(body.options):
        store.delete(key)

    for key, value in body.options.items():
        store.set(key, value)

    return PluginOptions(options=store.all())
