from pathlib import Path
from typing import Optional


from action_platform.core.wiring import wired
from action_platform.core.flow import git
from action_platform.core.flow.repository import Repository
from app.services.workspace import git_auth as auth
from app.repositories.configuration.config_store import ConfigStore
from app.repositories.workspace.registry import Registry
from app.schemas import PullRequestRequest, StartBranchRequest
from app.services.workspace import Workspaces
from app.core.errors import Conflict, Invalid, NotFound
from app.services.workspace.snapshot import SnapshotService


class FlowService:
    def __init__(self, registry: Registry, configs: ConfigStore | None = None) -> None:
        self.registry = registry
        self.configs = configs or ConfigStore(registry.store.database)

    def _root(self, id: str) -> Path:
        return Workspaces(self.registry).checkout(id)[1]

    def _repo(self, id: str) -> Repository:
        return Repository(self._root(id))

    def start_branch(self, id: str, body: StartBranchRequest) -> dict:
        with auth.git_auth(body.credentials):
            branch = wired.gitflow(self._repo(id)).start(
                body.kind, body.code, body.slug, push=True
            )

        self.registry.set_branch(id, branch.name)
        self._snapshot(id)

        return {"branch": branch.name, "base": branch.base, "pushed": True}

    def _snapshot(self, id: str) -> None:
        SnapshotService(self.registry, self.configs).take(id)

    def plan_branch(self, id: str, kind: str, code: str, slug: Optional[str]) -> dict:
        branch = wired.gitflow(self._repo(id)).plan_branch(kind, code or "code", slug)

        return {"branch": branch.name, "base": branch.base, "pushed": False}

    def checkout(self, id: str, branch: str) -> dict:
        try:
            git.check_ref(branch)
        except git.BadRef as e:
            raise Invalid(str(e)) from e

        if self.registry.drafts.paths(id):
            raise Conflict("commit or discard the pending changes first")

        repo = self._repo(id)
        repo.fetch(tags=False)

        if not repo.tracking_branch_exists(branch):
            raise NotFound(f"branch {branch} does not exist on the remote")

        self.registry.set_branch(id, branch)
        _, root = Workspaces(self.registry).refresh(id)
        self._snapshot(id)

        return {"branch": Repository(root).branch}

    def propose_pr(self, id: str, base: str | None, title: str | None) -> dict:
        proposal = wired.gitflow(self._repo(id)).propose(base=base, title=title)

        return {
            "head": proposal.head,
            "base": proposal.base,
            "title": proposal.title,
            "body": proposal.body,
            "commits": proposal.commits,
        }

    def open_pr(self, id: str, body: PullRequestRequest) -> dict:
        root = self._root(id)
        config = self.configs.config(id, root)
        auth.apply(config, body.credentials)

        with auth.git_auth(body.credentials):
            ref = wired.gitflow(root).open_pr(
                base=body.base,
                title=body.title,
                body=body.body,
                draft=body.draft,
                config=config,
            )

        return {"number": ref.number, "url": ref.url}
