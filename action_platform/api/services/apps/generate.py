"""Creating an app from a template: generated, pushed to the code host, registered."""

from __future__ import annotations

import shutil

from fastapi import HTTPException

from action_platform.api.core import credentials as auth
from action_platform.api.repositories.registry import Entry
from action_platform.api.schemas import InitRequest, PushRequest
from action_platform.api.services.catalog import TemplateRepos
from action_platform.core.manifest import write_source_host
from action_platform.core.scaffold.generate import (
    apply_cloud,
    generate_project,
    push_project,
)
from action_platform.settings import settings

from action_platform.api.services.apps.base import AppsBase


class AppScaffolding(AppsBase):
    def init(self, body: InitRequest) -> dict:
        repo, m = TemplateRepos.resolve(body.source)
        leaf = m.resolve(body.type, body.stack, body.template)
        id = self.registry.new_id()
        creds = body.credentials

        if not (creds and creds.kind and creds.token):
            raise HTTPException(
                400,
                "creating an app on the platform needs a source host to push it to: attach one, or generate it locally with the CLI",
            )

        staging = self.registry.workspaces / f".init-{id}"
        staging.mkdir(parents=True, exist_ok=True)

        extra = {"description": body.description}
        owner = body.github_owner or creds.owner

        if body.package_name:
            extra["package_name"] = body.package_name

        if owner:
            extra["github_owner"] = owner

        try:
            generated = generate_project(
                repo, leaf, name=body.name, ci=body.ci, output=staging, extra=extra
            )

            if body.cloud:
                apply_cloud(repo, m.cloud(body.cloud), generated)

            slug = generated.name
            path = self.registry.workspaces / id
            generated.rename(path)
        finally:
            shutil.rmtree(staging, ignore_errors=True)

        write_source_host(
            path / settings.CONFIG_FILE,
            creds.kind,
            f"{owner or 'me'}/{slug}",
            creds.base_url,
        )

        try:
            with auth.git_auth(creds):
                url = push_project(path, private=body.private, credentials=creds)
        except Exception:
            shutil.rmtree(path, ignore_errors=True)
            raise

        entry = self.registry.register(
            Entry(id=id, name=slug, url=url, path=str(path), default_branch="main")
        )

        return {
            "id": entry.id,
            "name": entry.name,
            "path": entry.path,
            "url": url,
            "template": leaf.directory,
            "cloud": body.cloud,
            "pushed": True,
        }

    def push(self, id: str, body: PushRequest) -> dict:
        entry = self.registry.get(id)

        raise HTTPException(
            409,
            f"{entry.name} was pushed to {entry.url} when it was created; apps on the platform always have a remote",
        )
