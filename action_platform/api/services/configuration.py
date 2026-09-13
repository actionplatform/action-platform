import tomllib
from pathlib import Path

from fastapi import HTTPException

from action_platform.api.core import credentials as auth
from action_platform.api.repositories.registry import Registry
from action_platform.api.schemas import CommitRequest
from action_platform.core.config import Config
from action_platform.core.flow import branching, git, gitflow, pullrequest
from action_platform.core.flow.branching import BranchError
from action_platform.core.scaffold.generate import apply_cloud, apply_service
from action_platform.core.scaffold.templates import TemplateError, load_matrix
from action_platform.settings import settings


class ConfigurationService:
    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    def _root(self, id: str) -> Path:
        root = Path(self.registry.get(id).path)

        if not root.is_dir():
            raise HTTPException(410, f"{root} no longer exists")

        return root

    def manifest(self, id: str) -> dict:
        return {"content": (self._root(id) / settings.CONFIG_FILE).read_text()}

    def write_manifest(self, id: str, content: str) -> dict:
        try:
            tomllib.loads(content)
        except tomllib.TOMLDecodeError as e:
            raise HTTPException(400, f"invalid TOML: {e}") from e

        path = self._root(id) / settings.CONFIG_FILE
        path.write_text(content if content.endswith("\n") else content + "\n")

        return {"content": path.read_text()}

    def set_cloud(self, id: str, target: str) -> dict:
        repo, matrix = load_matrix()

        try:
            apply_cloud(repo, matrix.cloud(target), self._root(id))
        except TemplateError as e:
            raise HTTPException(400, str(e)) from e

        return {"target": target}

    def add_service(self, id: str, name: str, provider: str | None) -> dict:
        repo, matrix = load_matrix()
        service = next((s for s in matrix.services if s.name == name), None)

        if service is None:
            raise HTTPException(400, f"unknown service: {name}")

        apply_service(repo, service, self._root(id), provider=provider)

        return {
            "name": name,
            "provider": provider or (service.providers[0] if service.providers else ""),
        }

    def commit(self, id: str, body: CommitRequest) -> dict:
        root = self._root(id)

        if git.is_clean(cwd=root):
            raise HTTPException(409, "nothing to commit")

        problem = gitflow.check_commit(body.message)

        if problem:
            raise HTTPException(400, problem)

        if body.branch:
            branch = self._branch_with_changes(root, body)
        else:
            branch = git.current_branch(cwd=root)
            problem = gitflow.check_protected(branch, body.message)

            if problem:
                raise HTTPException(400, problem)

        git.add_all(root)
        git.commit(body.message, cwd=root)
        sha = git.run(["rev-parse", "--short", "HEAD"], cwd=root)
        push = body.push or body.pull_request

        if push:
            with auth.git_auth(body.credentials):
                git.push_upstream(branch, root)

        result = {"sha": sha, "branch": branch, "pushed": push, "pull_request": None}

        if body.pull_request:
            config = Config.from_toml(root / settings.CONFIG_FILE)
            auth.apply(config, body.credentials)

            with auth.git_auth(body.credentials):
                ref = pullrequest.open_pr(root, config=config)

            result["pull_request"] = {"number": ref.number, "url": ref.url}

        return result

    def _branch_with_changes(self, root: Path, body: CommitRequest) -> str:
        spec = body.branch
        git.run(["stash", "push", "--include-untracked"], cwd=root)

        try:
            with auth.git_auth(body.credentials):
                branch = branching.start(spec.kind, spec.code, spec.slug, cwd=root, push=False)
        except BranchError as e:
            git.run(["stash", "pop"], cwd=root)
            raise HTTPException(400, str(e)) from e
        except Exception:
            git.run(["stash", "pop"], cwd=root)
            raise

        git.run(["stash", "pop"], cwd=root)

        return branch.name
