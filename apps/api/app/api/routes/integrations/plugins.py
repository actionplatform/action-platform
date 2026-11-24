"""Plugins on the hosted platform: the ones the image bundles, and a plugin's options — those belong to the caller's organization."""

from fastapi import APIRouter

from app.schemas.integrations import Plugins
from app.schemas.integrations import PluginOptions
from app.api.dependencies import CallerDep, OrgDep, PluginsDep, allowed
from app.services.integrations.plugins.options import secret_keys

router = APIRouter(prefix="/api/v1/plugins", tags=["plugins"])


@router.get("")
def plugins(org: OrgDep, caller: CallerDep, manager: PluginsDep) -> Plugins:
    return manager.catalog()


@router.get("/{slug}/options")
def plugin_options(
    slug: str, org: OrgDep, caller: CallerDep, manager: PluginsDep
) -> PluginOptions:
    allowed(caller, org, "org.manage")
    store = manager.options(slug, org.id)

    return PluginOptions(options=store.public(), secrets=store.stored_secrets())


@router.put("/{slug}/options")
def set_plugin_options(
    slug: str,
    body: PluginOptions,
    org: OrgDep,
    caller: CallerDep,
    manager: PluginsDep,
) -> PluginOptions:
    """Replaces the plugin's options with the body's; a key left out is deleted — except a secret, which a form never sees and so leaves out or sends empty to keep. `null` deletes a secret."""
    allowed(caller, org, "org.manage")
    store = manager.options(slug, org.id)
    secrets = set(store.stored_secrets()) | secret_keys(slug)

    for key in set(store.public()) - set(body.options):
        store.delete(key)

    for key, value in body.options.items():
        if key in secrets and value is None:
            store.delete(key)
        elif key in secrets and value == "":
            continue
        else:
            store.set(key, value)

    return PluginOptions(options=store.public(), secrets=store.stored_secrets())
