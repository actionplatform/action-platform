"""Turning a clone's pending changes into a commit: on the current branch, or on a new git-flow branch when the current one is protected, pushed, with a pull request when asked."""

from __future__ import annotations

from action_platform.core.flow import gitflow
from action_platform.core.flow.repository import Repository
from action_platform.core.flow.workflow import BranchError
from action_platform.core.wiring import wired
from app.core.errors import Conflict, Invalid
from app.services.workspace import git_auth as auth
from app.repositories.configuration.config_store import ConfigStore
from app.repositories.workspace.registry import Registry
from app.schemas import CommitRequest
from app.services.workspace.checkout import Workspaces


class CommitService:
    def __init__(self, registry: Registry, configs: ConfigStore | None = None) -> None:
        self.registry = registry
        self.configs = configs or ConfigStore(registry.store.database)

    def commit(self, id: str, body: CommitRequest) -> dict:
        entry, root = Workspaces(self.registry).refresh(id)
        repo = Repository(root)

        if repo.is_clean():
            raise Conflict("nothing to commit")

        problem = gitflow.check_commit(body.message)

        if problem:
            raise Invalid(problem)

        with auth.git_auth(body.credentials):
            if body.branch:
                branch = self._branch_with_changes(repo, body)
            else:
                branch = repo.branch
                problem = gitflow.check_protected(branch, body.message)

                if problem:
                    raise Invalid(problem)

            repo.add_all()
            repo.commit(body.message)
            sha = repo.short_head()
            push = True
            repo.push_upstream(branch)
            self.registry.drafts.clear(id)
            self.registry.set_branch(id, branch)

            result = {
                "sha": sha,
                "branch": branch,
                "pushed": push,
                "pull_request": None,
            }

            if body.pull_request:
                config = self.configs.config(id, root)
                auth.apply(config, body.credentials)
                ref = wired.gitflow(repo).open_pr(config=config)
                result["pull_request"] = {"number": ref.number, "url": ref.url}

        return result

    def _branch_with_changes(self, repo: Repository, body: CommitRequest) -> str:
        spec = body.branch

        with repo.stashed():
            try:
                branch = wired.gitflow(repo).start(
                    spec.kind, spec.code, spec.slug, push=False
                )
            except BranchError as e:
                raise Invalid(str(e)) from e

        return branch.name
