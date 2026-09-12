"""FastAPI app for the web frontend: apps registry (one git repo each), per-app state, actions.

Same core modules as the CLI and the MCP tools. Actions default to dry
runs; the frontend confirms before calling with dry_run=false.
"""

from __future__ import annotations

import os
import shutil
import tomllib
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from action_platform import __version__
from action_platform.api import credentials as auth
from action_platform.api import models
from action_platform.api.registry import Entry, Registry
from action_platform.core.flow import git, gitflow
from action_platform.core.action_platform import ActionPlatform
from action_platform.core.config import Config
from action_platform.core.exception import ActionPlatformError
from action_platform.core.manifest import write_source_host
from action_platform.core.scaffold.generate import (
    apply_cloud,
    generate_project,
    push_project,
)
from action_platform.core.scaffold.templates import load_matrix
from action_platform.settings import settings


class AddApp(BaseModel):
    url: str
    name: Optional[str] = None


class ReleaseRequest(BaseModel):
    level: str = "patch"
    dry_run: bool = True
    credentials: Optional[models.SourceCredentials] = None


class DeployRequest(BaseModel):
    stage: Optional[str] = None
    dry_run: bool = True


def _platform(root: Path) -> dict:
    data = tomllib.loads((root / settings.CONFIG_FILE).read_text())
    project = dict(data.get("project", {}))
    last = root / "LAST_VERSION"

    return {
        "project": project,
        "source_host": data.get("source_host", {}),
        "deploy": data.get("deploy", {}),
        "release": data.get("release", {}),
        "services": data.get("services", {}),
        "last_version": last.read_text().strip() if last.exists() else None,
    }


def build(cors_origins: Optional[list[str]] = None) -> FastAPI:
    app = FastAPI(title="action-platform", version=__version__)
    registry = Registry()

    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.exception_handler(ActionPlatformError)
    def _platform_error(_, exc: ActionPlatformError):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=400, content={"detail": str(exc)})

    def root_of(id: str) -> Path:
        entry = registry.get(id)
        root = Path(entry.path)

        if not root.is_dir():
            raise HTTPException(410, f"{root} no longer exists")

        return root

    @app.get("/api/version")
    def version() -> models.Version:
        return {"version": __version__}

    @app.get("/api/matrix")
    def matrix() -> models.Matrix:
        _, m = load_matrix()

        return {
            "projects": [
                {
                    "type": leaf.type,
                    "stack": leaf.stack,
                    "template": leaf.template,
                    "default": leaf.default,
                    "description": leaf.description,
                }
                for leaf in m.leaves
            ],
            "clouds": [
                {
                    "name": c.name,
                    "types": c.types,
                    "languages": c.languages,
                    "description": c.description,
                }
                for c in m.clouds
            ],
            "services": [
                {"name": s.name, "providers": s.providers, "description": s.description}
                for s in m.services
            ],
        }

    @app.get("/api/gitflow/rules")
    def gitflow_rules() -> models.GitflowRules:
        return {
            "kinds": sorted(gitflow.KINDS),
            "protected": sorted(gitflow.PROTECTED),
            "types": sorted(gitflow.TYPES),
        }

    @app.get("/api/apps")
    def list_apps() -> list[models.AppRow]:
        rows = []

        for entry in registry.list():
            root = Path(entry.path)
            row = asdict(entry)
            row["exists"] = root.is_dir()

            if row["exists"] and (root / settings.CONFIG_FILE).exists():
                info = _platform(root)
                row["language"] = info["project"].get("language")
                row["type"] = info["project"].get("type")
                row["last_version"] = info["last_version"]

                try:
                    row["branch"] = git.current_branch(cwd=root)
                except Exception:
                    row["branch"] = None

            rows.append(row)

        return rows

    @app.post("/api/apps", status_code=201)
    def add_app(body: AddApp) -> models.AppEntry:
        return asdict(registry.add(body.url, body.name))

    @app.post("/api/apps/init", status_code=201)
    def init_app(body: models.InitRequest) -> models.InitResult:
        """Generate an app from the matrix into a new workspace and register it.

        Nothing leaves the server unless `push` is set, which creates the
        remote repository through the template's [source_host].
        """
        repo, m = load_matrix()
        leaf = m.resolve(body.type, body.stack, body.template)
        id = registry.new_id()
        staging = registry.workspaces / f".init-{id}"
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
            path = registry.workspaces / id
            generated.rename(path)
        finally:
            shutil.rmtree(staging, ignore_errors=True)

        # The template hard-codes github; the chosen host wins.
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

        entry = registry.register(
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

    @app.post("/api/apps/{id}/push")
    def push_app(id: str, body: models.PushRequest) -> models.PushResult:
        """Create the remote repository through the app's [source_host] and push main.

        Needs ACTION_PLATFORM_GITHUB_TOKEN (or GH_TOKEN) in the API's environment.
        """
        entry = registry.get(id)
        root = root_of(id)

        if entry.url:
            raise HTTPException(409, f"already pushed to {entry.url}")

        if body.credentials:
            meta = _platform(root)
            repo = meta["source_host"].get("repo") or entry.name
            slug = repo.rsplit("/", 1)[-1]
            owner = body.credentials.owner or repo.split("/", 1)[0]
            write_source_host(
                root / settings.CONFIG_FILE,
                body.credentials.kind,
                f"{owner}/{slug}",
                body.credentials.base_url,
            )

        with auth.git_auth(body.credentials):
            url = push_project(root, private=body.private, credentials=body.credentials)
        entry.url = url
        entry.default_branch = entry.default_branch or "main"
        registry.register(entry)

        return {"id": id, "url": url}

    @app.post("/api/apps/{id}/sync")
    def sync_app(id: str) -> models.AppEntry:
        return asdict(registry.sync(id))

    @app.delete("/api/apps/{id}", status_code=204)
    def remove_app(id: str) -> None:
        registry.get(id)
        registry.remove(id)

    @app.get("/api/apps/{id}")
    def app_detail(id: str) -> models.AppDetail:
        entry = registry.get(id)
        root = root_of(id)
        info = _platform(root)
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

    @app.get("/api/apps/{id}/gitflow")
    def app_gitflow(id: str) -> models.GitflowReport:
        report = gitflow.audit(root_of(id))
        data = asdict(report)
        data["ok"] = report.ok

        return data

    @app.get("/api/apps/{id}/commits")
    def app_commits(id: str, limit: int = 20) -> list[models.Commit]:
        out = git.run(
            ["log", f"-{limit}", "--format=%h%x1f%s%x1f%an%x1f%ad", "--date=short"],
            cwd=root_of(id),
        )

        return [
            dict(zip(("sha", "subject", "author", "date"), line.split("\x1f")))
            for line in out.splitlines()
            if line
        ]

    @app.get("/api/apps/{id}/tags")
    def app_tags(id: str) -> list[str]:
        return list(reversed(git.tags(cwd=root_of(id))))

    @app.get("/api/apps/{id}/branches")
    def app_branches(id: str) -> list[models.Branch]:
        # Remote branches: the workspace is a clone and only checks out one.
        out = git.run(
            [
                "for-each-ref",
                "--sort=-committerdate",
                "--format=%(refname:short)|%(committerdate:short)",
                "refs/remotes/origin",
            ],
            cwd=root_of(id),
        )
        rows = [line.rsplit("|", 1) for line in out.splitlines() if line]
        names = [
            (ref.removeprefix("origin/"), date)
            for ref, date in rows
            if ref != "origin/HEAD"
        ]

        return [
            {
                "name": name,
                "date": date,
                "kind": gitflow.kind_of(name),
                "protected": name in gitflow.PROTECTED,
                "problem": gitflow.check_branch(name),
            }
            for name, date in names
        ]

    def tool(root: Path) -> ActionPlatform:
        return ActionPlatform(
            config=Config.from_toml(root / settings.CONFIG_FILE), repo_root=root
        )

    @app.post("/api/apps/{id}/release")
    def app_release(id: str, body: ReleaseRequest) -> models.ReleasePreview:
        platform = auth.apply(tool(root_of(id)), body.credentials)

        with auth.git_auth(body.credentials):
            ctx = platform.release(level=body.level, dry_run=body.dry_run)

        return {
            "current": ctx.current_version,
            "next": ctx.next_version,
            "changelog": ctx.changelog,
            "dry_run": body.dry_run,
        }

    @app.post("/api/apps/{id}/deploy")
    def app_deploy(id: str, body: DeployRequest) -> list[models.DeployResult]:
        results = tool(root_of(id)).deploy(stage=body.stage, dry_run=body.dry_run)

        return [
            {
                "target": r.target,
                "ok": r.ok,
                "version": r.version,
                "url": r.url,
                "error": r.error,
            }
            for r in results
        ]

    @app.get("/api/apps/{id}/diagnose")
    def app_diagnose(id: str, stage: Optional[str] = None) -> list[models.Diagnosis]:
        results = tool(root_of(id)).diagnose(stage=stage)

        return [asdict(r) for r in results]

    return app


def create_app() -> FastAPI:
    """Factory for uvicorn --reload; origins come from AP_CORS (comma-separated)."""
    origins = [o for o in os.environ.get("AP_CORS", "").split(",") if o]

    return build(origins or None)


def serve(
    host: str,
    port: int,
    cors_origins: Optional[list[str]] = None,
    reload: bool = False,
) -> None:
    import uvicorn

    if reload:
        os.environ["AP_CORS"] = ",".join(cors_origins or [])
        uvicorn.run(
            "action_platform.api.server:create_app",
            factory=True,
            host=host,
            port=port,
            reload=True,
            reload_dirs=[str(Path(__file__).resolve().parents[1])],
            log_level="info",
        )
        return

    uvicorn.run(build(cors_origins), host=host, port=port, log_level="warning")
