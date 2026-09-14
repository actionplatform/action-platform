import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from action_platform.api.core import credentials as auth
from action_platform.api.repositories.registry import Entry, MissingManifest, Registry
from action_platform.api.schemas import (
    InitRequest,
    InstallSpec,
    PushRequest,
    SourceCredentials,
)
from action_platform.api.services.manifest import read_manifest
from action_platform.api.services.workspace import Workspaces
from action_platform.core.flow.repository import Repository
from action_platform.core.scaffold.install import InstallError, install
from action_platform.core.manifest import write_source_host
from action_platform.core.scaffold.generate import (
    apply_cloud,
    generate_project,
    push_project,
)
from action_platform.api.services.catalog import resolve_repo
from action_platform.api.services.directory import kind_of_url, repo_from_url
from action_platform.core.exception import ProviderError
from action_platform.providers.source import build_source_host
from action_platform.settings import settings


class AppService:
    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    def workspace(self, id: str) -> tuple[Entry, Path]:
        return Workspaces(self.registry).checkout(id)

    def list(self) -> list[dict]:
        """Every app with what the manifest says about it. Listing clones nothing: an app not checked out on this instance answers with its registry row only."""
        rows = []

        for entry in self.registry.list():
            root = Path(entry.path)
            row = asdict(entry)
            row["exists"] = bool(entry.url)
            row["branch"] = entry.checked_out

            if root.is_dir() and (root / settings.CONFIG_FILE).exists():
                info = read_manifest(root)
                row["language"] = info["project"].get("language")
                row["type"] = info["project"].get("type")
                row["last_version"] = info["last_version"]

            rows.append(row)

        return rows

    def add(
        self,
        url: str,
        name: Optional[str],
        credentials: Optional[SourceCredentials] = None,
        install_spec: Optional[InstallSpec] = None,
    ) -> dict:
        with auth.git_auth(credentials):
            try:
                entry = self.registry.add(
                    url, name, require_manifest=install_spec is None
                )
            except MissingManifest as e:
                raise HTTPException(
                    422, {"code": "needs_install", "detail": str(e)}
                ) from e

        result = asdict(entry)
        root = Path(entry.path)

        if install_spec is not None and not (root / settings.CONFIG_FILE).exists():
            try:
                plan = install(
                    root,
                    type_=install_spec.type,
                    language=install_spec.language,
                    ci=install_spec.ci,
                    name=entry.name,
                )
            except InstallError as e:
                self.registry.remove(entry.id)
                raise HTTPException(400, str(e)) from e

            result["installed"] = plan.created

            if self.registry.drafts is not None:
                self.registry.drafts.capture(entry.id, root)

        return result

    def sync(
        self,
        id: str,
        credentials: Optional[SourceCredentials] = None,
        reset: bool = False,
    ) -> dict:
        if reset:
            self.registry.drafts.clear(id)

        with auth.git_auth(credentials):
            entry, _ = Workspaces(self.registry).refresh(id)

        return asdict(entry)

    def remove(self, id: str) -> None:
        entry = self.registry.get(id)
        self.registry.remove(id)
        Workspaces(self.registry).drop(id, Path(entry.path))

    def repository_of(self, id: str) -> Optional[tuple[str, str]]:
        """(kind, owner/name) of the remote this app was pushed to or added from; None when it has none."""
        entry, root = self.workspace(id)

        if not entry.url:
            return None

        try:
            host = read_manifest(root)["source_host"]
        except HTTPException:
            host = {}

        repo = host.get("repo") or repo_from_url(entry.url)
        kind = host.get("kind") or kind_of_url(entry.url)

        if not repo or not kind:
            return None

        return kind, repo

    def delete_repository(self, id: str, credentials: SourceCredentials) -> str:
        """Delete the remote repository behind the app with `credentials`; returns owner/name."""
        remote = self.repository_of(id)

        if remote is None:
            raise HTTPException(409, "this app has no remote repository")

        kind, repo = remote

        if credentials.kind and credentials.kind != kind:
            raise HTTPException(
                409,
                f"the app lives on {kind}; the connected host is {credentials.kind}",
            )

        host = build_source_host(
            kind,
            repo,
            base_url=credentials.base_url,
            token=credentials.token,
            username=credentials.username,
        )

        try:
            host.delete_repository(repo)
        except NotImplementedError as e:
            raise HTTPException(409, str(e)) from e
        except ProviderError as e:
            raise HTTPException(502, str(e)) from e

        return repo

    def detail(self, id: str) -> dict:
        entry, root = self.workspace(id)
        info = read_manifest(root)
        info["id"] = id
        info["url"] = entry.url
        info["default_branch"] = entry.default_branch

        repo = Repository(root)
        info["branch"] = repo.branch if repo.exists() else entry.checked_out
        info["latest_tag"] = repo.latest_tag() if repo.exists() else None
        info["clean"] = not self.registry.drafts.paths(id)

        return info

    def init(self, body: InitRequest) -> dict:
        repo, m = resolve_repo(body.source)
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
