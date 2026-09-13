from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from action_platform.api.core import credentials as auth
from action_platform.api.repositories.registry import Registry
from action_platform.api.schemas import DeployRequest, ReleaseRequest
from action_platform.api.services.manifest import workspace_of
from action_platform.core.action_platform import ActionPlatform
from action_platform.core.config import Config
from action_platform.core.flow import git
from action_platform.settings import settings


class LifecycleService:
    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    def _tool(self, id: str) -> ActionPlatform:
        _, root = workspace_of(self.registry, id)

        return ActionPlatform(
            config=Config.from_toml(root / settings.CONFIG_FILE), repo_root=root
        )

    def release(self, id: str, body: ReleaseRequest) -> dict:
        platform = self._tool(id)
        auth.apply(platform.config, body.credentials)

        with auth.git_auth(body.credentials):
            if body.branch:
                self._switch(platform.repo_root, body.branch)

            if not body.dry_run:
                self.registry.sync(id)

            ctx = platform.release(
                level=body.level, dry_run=body.dry_run, component=body.component
            )

        return {
            "current": ctx.current_version,
            "next": ctx.next_version,
            "changelog": ctx.changelog,
            "branch": ctx.branch,
            "prerelease": ctx.branch not in {"main", "master"},
            "dry_run": body.dry_run,
        }

    def _switch(self, root: Path, branch: str) -> None:
        try:
            git.check_ref(branch)
        except git.BadRef as e:
            raise HTTPException(400, str(e)) from e

        if git.current_branch(cwd=root) == branch:
            return

        if not git.is_clean(cwd=root):
            raise HTTPException(
                409,
                "working tree is dirty — commit or discard changes before releasing from another branch",
            )

        git.run(["fetch", "--prune", "origin"], cwd=root)

        try:
            git.checkout_branch(branch, cwd=root)
        except Exception as e:
            raise HTTPException(400, f"cannot check out {branch}: {e}") from e

        git.run(["pull", "--ff-only", "--end-of-options", "origin", branch], cwd=root)

    def deploy(self, id: str, body: DeployRequest) -> list[dict]:
        results = self._tool(id).deploy(stage=body.stage, dry_run=body.dry_run)

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

    def diagnose(self, id: str, stage: Optional[str]) -> list[dict]:
        return [asdict(r) for r in self._tool(id).diagnose(stage=stage)]
