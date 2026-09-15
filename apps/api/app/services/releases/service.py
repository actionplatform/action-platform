"""App › Releases: cut a release from a branch and preview the next version — the core's releaser on the app's clone with the configuration the platform keeps."""

from pathlib import Path
from typing import Callable, Optional


from action_platform.core.action_platform import ActionPlatform
from action_platform.core.flow import git
from action_platform.core.flow.repository import Repository
from action_platform.core.release.components import resolve
from action_platform.core.release.release import STABLE_BRANCHES
from app.core.shared import git_auth as auth
from app.repositories.configuration.config_store import ConfigStore
from app.repositories.workspace.registry import Registry
from app.schemas import ReleaseRequest
from app.services.workspace import Workspaces
from app.core.errors import Conflict, Invalid


class ReleasesService:
    def __init__(
        self,
        registry: Registry,
        identity: Callable[[str], str] | None = None,
        env: dict[str, str] | None = None,
        configs: ConfigStore | None = None,
    ) -> None:
        self.registry = registry
        self.identity = identity
        self.env = env
        self.configs = configs or ConfigStore(registry.store.database)

    def _tool(self, id: str, fresh: bool = False) -> ActionPlatform:
        _, root = Workspaces(self.registry).checkout(id, fresh=fresh)

        return ActionPlatform(
            config=self.configs.config(id, root),
            repo_root=root,
            identity=self.identity,
            env=self.env,
        )

    def release(self, id: str, body: ReleaseRequest) -> dict:
        platform = self._tool(id, fresh=not body.dry_run)
        auth.apply(platform.config, body.credentials)

        with auth.git_auth(body.credentials):
            if body.branch:
                self._switch(platform.repo_root, body.branch)

            ctx = platform.release(
                level=body.level,
                dry_run=body.dry_run,
                component=body.component,
                name=body.name,
                notes=body.notes,
                latest=body.latest,
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
            raise Invalid(str(e)) from e

        repo = Repository(root)

        if repo.branch == branch:
            return

        if not repo.is_clean():
            raise Conflict(
                "working tree is dirty — commit or discard changes before releasing from another branch",
            )

        repo.fetch(tags=False)

        try:
            repo.checkout(branch)
        except Exception as e:
            raise Invalid(f"cannot check out {branch}: {e}") from e

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
