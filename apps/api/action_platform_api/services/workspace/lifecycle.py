from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from action_platform_api.core.shared import git_auth as auth
from action_platform_api.repositories.registry import Registry
from action_platform_api.schemas import DeployRequest, ReleaseRequest
from action_platform_api.services.workspace import Workspaces
from action_platform.core.action_platform import ActionPlatform
from action_platform.core.config import Config
from action_platform.core.flow import git
from action_platform.core.flow.repository import Repository
from action_platform.core.release.components import resolve
from action_platform.core.release.release import STABLE_BRANCHES
from action_platform.settings import settings


class LifecycleService:
    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    def _tool(self, id: str, fresh: bool = False) -> ActionPlatform:
        _, root = Workspaces(self.registry).checkout(id, fresh=fresh)

        return ActionPlatform(
            config=Config.from_toml(root / settings.CONFIG_FILE), repo_root=root
        )

    def release(self, id: str, body: ReleaseRequest) -> dict:
        platform = self._tool(id, fresh=not body.dry_run)
        auth.apply(platform.config, body.credentials)

        with auth.git_auth(body.credentials):
            if body.branch:
                self._switch(platform.repo_root, body.branch)

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

        repo = Repository(root)

        if repo.branch == branch:
            return

        if not repo.is_clean():
            raise HTTPException(
                409,
                "working tree is dirty — commit or discard changes before releasing from another branch",
            )

        repo.fetch(tags=False)

        try:
            repo.checkout(branch)
        except Exception as e:
            raise HTTPException(400, f"cannot check out {branch}: {e}") from e

        repo.run(["pull", "--ff-only", "--end-of-options", "origin", branch])

    def next_version(
        self, id: str, level: str, branch: Optional[str], component: Optional[str]
    ) -> dict:
        platform = self._tool(id)
        current = platform.releaser.current_version(
            resolve(platform.config.components, component)
        )
        chosen = branch or platform.repo.branch

        return {
            "current": current,
            "next": platform.releaser.next_version(
                level, component=component, branch=chosen
            ),
            "branch": chosen,
            "prerelease": chosen not in STABLE_BRANCHES,
        }

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
