"""FastAPI app for the web frontend: projects registry, per-project state, actions.

Same core modules as the CLI and the MCP tools. Actions default to dry
runs; the frontend confirms before calling with dry_run=false.
"""

from __future__ import annotations

import tomllib
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from action_platform import __version__
from action_platform.api import models
from action_platform.api.registry import Registry
from action_platform.core import git, gitflow
from action_platform.core.action_platform import ActionPlatform
from action_platform.core.config import Config
from action_platform.core.exception import ActionPlatformError
from action_platform.core.templates import load_matrix
from action_platform.settings import settings


class AddProject(BaseModel):
    path: str


class ReleaseRequest(BaseModel):
    level: str = "patch"
    dry_run: bool = True


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

    @app.get("/api/projects")
    def list_projects() -> list[models.ProjectRow]:
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

    @app.post("/api/projects", status_code=201)
    def add_project(body: AddProject) -> models.ProjectEntry:
        return asdict(registry.add(Path(body.path).expanduser()))

    @app.delete("/api/projects/{id}", status_code=204)
    def remove_project(id: str) -> None:
        registry.get(id)
        registry.remove(id)

    @app.get("/api/projects/{id}")
    def project(id: str) -> models.ProjectDetail:
        root = root_of(id)
        info = _platform(root)
        info["id"] = id
        info["path"] = str(root)
        info["branch"] = git.current_branch(cwd=root)
        info["latest_tag"] = git.latest_tag(cwd=root)
        info["clean"] = git.is_clean(cwd=root)

        return info

    @app.get("/api/projects/{id}/gitflow")
    def project_gitflow(id: str) -> models.GitflowReport:
        report = gitflow.audit(root_of(id))
        data = asdict(report)
        data["ok"] = report.ok

        return data

    @app.get("/api/projects/{id}/commits")
    def project_commits(id: str, limit: int = 20) -> list[models.Commit]:
        out = git.run(
            ["log", f"-{limit}", "--format=%h%x1f%s%x1f%an%x1f%ad", "--date=short"],
            cwd=root_of(id),
        )

        return [
            dict(zip(("sha", "subject", "author", "date"), line.split("\x1f")))
            for line in out.splitlines()
            if line
        ]

    @app.get("/api/projects/{id}/tags")
    def project_tags(id: str) -> list[str]:
        return list(reversed(git.tags(cwd=root_of(id))))

    @app.get("/api/projects/{id}/branches")
    def project_branches(id: str) -> list[models.Branch]:
        root = root_of(id)
        out = git.run(
            [
                "for-each-ref",
                "--sort=-committerdate",
                "--format=%(refname:short)|%(committerdate:short)",
                "refs/heads",
            ],
            cwd=root,
        )
        rows = [line.rsplit("|", 1) for line in out.splitlines() if line]

        return [
            {
                "name": name,
                "date": date,
                "kind": gitflow.kind_of(name),
                "protected": name in gitflow.PROTECTED,
                "problem": gitflow.check_branch(name),
            }
            for name, date in rows
        ]

    def tool(root: Path) -> ActionPlatform:
        return ActionPlatform(
            config=Config.from_toml(root / settings.CONFIG_FILE), repo_root=root
        )

    @app.post("/api/projects/{id}/release")
    def project_release(id: str, body: ReleaseRequest) -> models.ReleasePreview:
        ctx = tool(root_of(id)).release(level=body.level, dry_run=body.dry_run)

        return {
            "current": ctx.current_version,
            "next": ctx.next_version,
            "changelog": ctx.changelog,
            "dry_run": body.dry_run,
        }

    @app.post("/api/projects/{id}/deploy")
    def project_deploy(id: str, body: DeployRequest) -> list[models.DeployResult]:
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

    @app.get("/api/projects/{id}/diagnose")
    def project_diagnose(
        id: str, stage: Optional[str] = None
    ) -> list[models.Diagnosis]:
        results = tool(root_of(id)).diagnose(stage=stage)

        return [asdict(r) for r in results]

    return app


def serve(host: str, port: int, cors_origins: Optional[list[str]] = None) -> None:
    import uvicorn

    uvicorn.run(build(cors_origins), host=host, port=port, log_level="warning")
