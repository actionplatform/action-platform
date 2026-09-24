"""App › Deployments: ship a release to the app's deploy target and read what is live — the core's deployer on the app's clone, with the identity and the environment the platform signs and fills."""

from dataclasses import asdict
from typing import Callable, Optional

from sqlalchemy import select

from action_platform.core.facade import ActionPlatform
from app.core.db.models import App
from app.repositories.configuration.config_store import ConfigStore
from app.repositories.scopes import ScopeStore
from app.repositories.workspace.registry import Registry
from app.schemas import DeployRequest, SourceCredentials
from app.services.scopes import ScopesService
from app.services.workspace import Workspaces
from app.services.workspace import git_auth as auth


class DeploymentsService:
    def __init__(
        self,
        registry: Registry,
        identity: Callable[[str], str] | None = None,
        env: dict[str, str] | None = None,
        configs: ConfigStore | None = None,
        credentials: SourceCredentials | None = None,
    ) -> None:
        self.registry = registry
        self.identity = identity
        self.env = env
        self.configs = configs or ConfigStore(registry.store.database)
        self.credentials = credentials

    def _scopes(self, id: str) -> list[dict]:
        """The app's scopes as the platform keeps them, in place of whatever platform.toml says; an app the platform does not know keeps the file's."""
        with self.registry.store.database.session() as db:
            app = db.scalar(select(App).where(App.registry_id == id))

            if app is None:
                return []

            return [
                ScopeStore.as_toml(spec)
                for spec in ScopesService(db, self.configs).specs(app)
            ]

    def _tool(self, id: str) -> ActionPlatform:
        _, root = Workspaces(self.registry).checkout(id)
        config = auth.apply(self.configs.config(id, root), self.credentials)
        config._scopes_spec = self._scopes(id)

        return ActionPlatform(
            config=config,
            repo_root=root,
            identity=self.identity,
            env=self.env,
        )

    def deploy(self, id: str, body: DeployRequest) -> list[dict]:
        results = self._tool(id).deploy(
            stage=body.scope or body.stage, dry_run=body.dry_run, version=body.version
        )

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

    def destroy(self, id: str, stages: tuple[str, ...] | None = None) -> None:
        """Every scope's stack down — the app's scopes unless `stages` names them."""
        tool = self._tool(id)

        for stage in stages or tuple(s["name"] for s in self._scopes(id)):
            tool.destroy(stage=stage)

    def diagnose(self, id: str, stage: Optional[str]) -> list[dict]:
        return [asdict(r) for r in self._tool(id).diagnose(stage=stage)]
