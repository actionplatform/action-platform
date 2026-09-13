import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from action_platform.api.core import credentials as auth
from action_platform.api.repositories.registry import Entry, Registry
from action_platform.api.schemas import InitRequest, PushRequest, SourceCredentials
from action_platform.api.services.manifest import read_manifest
from action_platform.core.flow import git, gitflow
from action_platform.core.manifest import write_source_host
from action_platform.core.scaffold.generate import (
    apply_cloud,
    generate_project,
    push_project,
)
from action_platform.core.scaffold.templates import load_matrix
from action_platform.settings import settings


class AppService:
    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    def workspace(self, id: str) -> tuple[Entry, Path]:
        entry = self.registry.get(id)
        root = Path(entry.path)

        if not root.is_dir():
            raise HTTPException(410, f"{root} no longer exists")

        return entry, root

    def list(self) -> list[dict]:
        rows = []

        for entry in self.registry.list():
            root = Path(entry.path)
            row = asdict(entry)
            row["exists"] = root.is_dir()

            if row["exists"] and (root / settings.CONFIG_FILE).exists():
                info = read_manifest(root)
                row["language"] = info["project"].get("language")
                row["type"] = info["project"].get("type")
                row["last_version"] = info["last_version"]

                try:
                    row["branch"] = git.current_branch(cwd=root)
                except Exception:
                    row["branch"] = None

            rows.append(row)

        return rows

    def add(self, url: str, name: Optional[str]) -> dict:
        return asdict(self.registry.add(url, name))

    def sync(self, id: str) -> dict:
        return asdict(self.registry.sync(id))

    def remove(self, id: str) -> None:
        self.registry.get(id)
        self.registry.remove(id)

    def detail(self, id: str) -> dict:
        entry, root = self.workspace(id)
        info = read_manifest(root)
        info["id"] = id
        info["url"] = entry.url
        info["default_branch"] = entry.default_branch

        if (root / ".git").is_dir():
            info["branch"] = git.current_branch(cwd=root)
            info["latest_tag"] = git.latest_tag(cwd=root)
            info["clean"] = git.is_clean(cwd=root)
        else:
            info["branch"] = ""
            info["latest_tag"] = None
            info["clean"] = True

        return info

    def init(self, body: InitRequest) -> dict:
        repo, m = load_matrix()
        leaf = m.resolve(body.type, body.stack, body.template)
        id = self.registry.new_id()
        staging = self.registry.workspaces / f".init-{id}"
        staging.mkdir(parents=True, exist_ok=True)

        extra = {"description": body.description}
        creds = body.credentials
        owner = body.github_owner or (creds.owner if creds else None)

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

        if creds:
            write_source_host(
                path / settings.CONFIG_FILE,
                creds.kind,
                f"{owner or 'me'}/{slug}",
                creds.base_url,
            )

        url = ""

        if body.push:
            with auth.git_auth(creds):
                url = push_project(path, private=body.private, credentials=creds)
        elif body.git_init:
            git.init(path, branch="main")
            gitflow.install_hooks(path)
            git.add_all(path)
            git.run(
                ["commit", "-q", "-m", "chore: bootstrap project from action-platform"],
                cwd=path,
            )

        entry = self.registry.register(
            Entry(
                id=id,
                name=slug,
                url=url,
                path=str(path),
                default_branch="main" if (body.push or body.git_init) else "",
            )
        )

        return {
            "id": entry.id,
            "name": entry.name,
            "path": entry.path,
            "url": url,
            "template": leaf.directory,
            "cloud": body.cloud,
            "pushed": bool(url),
        }

    def push(self, id: str, body: PushRequest) -> dict:
        entry, root = self.workspace(id)

        if entry.url:
            raise HTTPException(409, f"already pushed to {entry.url}")

        if body.credentials:
            self._point_source_host(root, entry, body.credentials)

        with auth.git_auth(body.credentials):
            url = push_project(root, private=body.private, credentials=body.credentials)

        entry.url = url
        entry.default_branch = entry.default_branch or "main"
        self.registry.register(entry)

        return {"id": id, "url": url}

    def _point_source_host(
        self, root: Path, entry: Entry, creds: SourceCredentials
    ) -> None:
        meta = read_manifest(root)
        repo = meta["source_host"].get("repo") or entry.name
        slug = repo.rsplit("/", 1)[-1]
        owner = creds.owner or repo.split("/", 1)[0]
        write_source_host(
            root / settings.CONFIG_FILE, creds.kind, f"{owner}/{slug}", creds.base_url
        )
