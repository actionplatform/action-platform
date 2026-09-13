from pathlib import Path

from fastapi import HTTPException

from action_platform.api.core import credentials as auth
from action_platform.api.repositories.registry import Registry
from action_platform.api.services.manifest import workspace_of
from action_platform.api.schemas import PullRequestRequest, StartBranchRequest
from action_platform.core.config import Config
from action_platform.core.flow import git
from action_platform.core.flow.repository import Repository
from action_platform.core.flow.workflow import GitFlow
from action_platform.settings import settings


class FlowService:
    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    def _root(self, id: str) -> Path:
        return workspace_of(self.registry, id)[1]

    def _repo(self, id: str) -> Repository:
        return Repository(self._root(id))

    def start_branch(self, id: str, body: StartBranchRequest) -> dict:
        with auth.git_auth(body.credentials):
            branch = GitFlow(self._repo(id)).start(
                body.kind, body.code, body.slug, push=body.push
            )

        return {"branch": branch.name, "base": branch.base, "pushed": branch.pushed}

    def checkout(self, id: str, branch: str) -> dict:
        repo = self._repo(id)

        try:
            git.check_ref(branch)
        except git.BadRef as e:
            raise HTTPException(400, str(e)) from e

        if not repo.is_clean():
            raise HTTPException(409, "working tree is dirty")

        repo.fetch(tags=False)
        repo.checkout(branch)

        return {"branch": repo.branch}

    def propose_pr(self, id: str, base: str | None, title: str | None) -> dict:
        proposal = GitFlow(self._repo(id)).propose(base=base, title=title)

        return {
            "head": proposal.head,
            "base": proposal.base,
            "title": proposal.title,
            "body": proposal.body,
            "commits": proposal.commits,
        }

    def open_pr(self, id: str, body: PullRequestRequest) -> dict:
        root = self._root(id)
        config = Config.from_toml(root / settings.CONFIG_FILE)
        auth.apply(config, body.credentials)

        with auth.git_auth(body.credentials):
            ref = GitFlow(root).open_pr(
                base=body.base,
                title=body.title,
                body=body.body,
                draft=body.draft,
                config=config,
            )

        return {"number": ref.number, "url": ref.url}
