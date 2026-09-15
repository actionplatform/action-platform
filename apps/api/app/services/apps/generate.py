"""Creating an app from a template: generated, pushed to the code host, registered."""

from __future__ import annotations

import shutil


from action_platform.core.wiring import wired
from action_platform.core.manifest import write_source_host
from action_platform.settings import settings
from app.core.shared import git_auth as auth
from app.repositories.registry import Entry
from app.schemas import InitRequest, PushRequest
from app.services.apps.base import AppsBase
from app.services.catalog import TemplateRepos
from app.core.errors import Conflict, Invalid


class AppScaffolding(AppsBase):
    def init(self, body: InitRequest) -> dict:
        repo, m = TemplateRepos.resolve(body.source)
        leaf = m.resolve(body.type, body.stack, body.template)
        id = self.registry.new_id()
        creds = body.credentials

        if not (creds and creds.kind and creds.token):
            raise Invalid(
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
            generated = wired.scaffolder().generate(
                repo, leaf, name=body.name, ci=body.ci, output=staging, extra=extra
            )

            if body.cloud:
                wired.scaffolder().apply_cloud(repo, m.cloud(body.cloud), generated)

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
                url = wired.scaffolder().push(
                    path, private=body.private, credentials=creds
                )
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

        raise Conflict(
            f"{entry.name} was pushed to {entry.url} when it was created; apps on the platform always have a remote",
        )
