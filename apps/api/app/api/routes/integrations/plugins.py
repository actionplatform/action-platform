"""Plugins on the hosted platform: the ones the image bundles, and a plugin's options — those belong to the caller's organization."""

from fastapi import APIRouter

from app.schemas.integrations import Plugins
from app.schemas.integrations import PluginOptions
from app.api.dependencies import CallerDep, OrgDep, PluginsDep, allowed

router = APIRouter(prefix="/api/v1/plugins", tags=["plugins"])


@router.get("")
def plugins(org: OrgDep, caller: CallerDep, manager: PluginsDep) -> Plugins:
    return manager.catalog()


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
