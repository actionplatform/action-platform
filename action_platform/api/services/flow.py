from pathlib import Path

from fastapi import HTTPException

from action_platform.api.core import credentials as auth
from action_platform.api.repositories.registry import Registry
from action_platform.api.schemas import PullRequestRequest, StartBranchRequest
from action_platform.core.config import Config
from action_platform.core.flow import branching, git, pullrequest
from action_platform.settings import settings


class FlowService:
    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    def _root(self, id: str) -> Path:
        root = Path(self.registry.get(id).path)

        if not root.is_dir():
            raise HTTPException(410, f"{root} no longer exists")

        return root

    def start_branch(self, id: str, body: StartBranchRequest) -> dict:
        with auth.git_auth(body.credentials):
            branch = branching.start(
                body.kind, body.code, body.slug, cwd=self._root(id), push=body.push
            )

        return {"branch": branch.name, "base": branch.base, "pushed": branch.pushed}

    def checkout(self, id: str, branch: str) -> dict:
        root = self._root(id)

        if not git.is_clean(cwd=root):
            raise HTTPException(409, "working tree is dirty")

        git.run(["fetch", "--prune", "origin"], cwd=root)
        git.checkout_branch(branch, cwd=root)

        return {"branch": git.current_branch(cwd=root)}

    def propose_pr(self, id: str, base: str | None, title: str | None) -> dict:
        proposal = pullrequest.propose(self._root(id), base=base, title=title)

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
            ref = pullrequest.open_pr(
                root,
                base=body.base,
                title=body.title,
                body=body.body,
                draft=body.draft,
                config=config,
            )

        return {"number": ref.number, "url": ref.url}
