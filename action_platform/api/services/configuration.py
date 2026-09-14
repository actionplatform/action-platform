import tomllib
from pathlib import Path

from fastapi import HTTPException

from action_platform.api.core import credentials as auth
from action_platform.api.repositories.registry import Registry
from action_platform.api.schemas import CommitRequest, SourceSpec
from action_platform.api.services.catalog import resolve_repo
from action_platform.api.services.workspace import Workspaces
from action_platform.core.config import Config
from action_platform.core.flow import gitflow
from action_platform.core.flow.repository import Repository
from action_platform.core.flow.workflow import BranchError, GitFlow
from action_platform.core.scaffold.install import install
from action_platform.core.scaffold.generate import apply_cloud, apply_service
from action_platform.core.scaffold.templates import TemplateError
from action_platform.settings import settings


class ConfigurationService:
    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    def _root(self, id: str) -> Path:
        return Workspaces(self.registry).checkout(id)[1]

    def _drafted(self, id: str, root: Path) -> list[str]:
        return self.registry.drafts.capture(id, root)

    def manifest(self, id: str) -> dict:
        manifest = self._root(id) / settings.CONFIG_FILE

        if not manifest.exists():
            raise HTTPException(
                400, f"{settings.CONFIG_FILE} not found in {manifest.parent}"
            )

        return {"content": manifest.read_text()}

    def write_manifest(self, id: str, content: str) -> dict:
        try:
            tomllib.loads(content)
        except tomllib.TOMLDecodeError as e:
            raise HTTPException(400, f"invalid TOML: {e}") from e

        root = self._root(id)
        path = root / settings.CONFIG_FILE
        path.write_text(content if content.endswith("\n") else content + "\n")
        self._drafted(id, root)

        return {"content": path.read_text()}

    def set_cloud(self, id: str, target: str, source: SourceSpec | None = None) -> dict:
        repo, matrix = resolve_repo(source)

        root = self._root(id)

        try:
            apply_cloud(repo, matrix.cloud(target), root)
        except TemplateError as e:
            raise HTTPException(400, str(e)) from e

        self._drafted(id, root)

        return {"target": target}

    def add_service(
        self, id: str, name: str, provider: str | None, source: SourceSpec | None = None
    ) -> dict:
        repo, matrix = resolve_repo(source)
        service = next((s for s in matrix.services if s.name == name), None)

        if service is None:
            raise HTTPException(400, f"unknown service: {name}")

        root = self._root(id)
        apply_service(repo, service, root, provider=provider)
        self._drafted(id, root)

        return {
            "name": name,
            "provider": provider or (service.providers[0] if service.providers else ""),
        }

    def changes(self, id: str) -> dict:
        files = self.registry.drafts.paths(id)

        return {"files": files, "clean": not files}

    def discard(self, id: str) -> dict:
        self.registry.drafts.clear(id)
        Workspaces(self.registry).refresh(id)

        return {"clean": True, "files": []}

    def install_platform(
        self, id: str, type_: str, language: str | None, ci: str | None
    ) -> dict:
        entry, root = Workspaces(self.registry).checkout(id)
        plan = install(root, type_=type_, language=language, ci=ci, name=entry.name)
        self._drafted(id, root)

        return {"installed": plan.created}

    def commit(self, id: str, body: CommitRequest) -> dict:
        entry, root = Workspaces(self.registry).refresh(id)
        repo = Repository(root)

        if repo.is_clean():
            raise HTTPException(409, "nothing to commit")

        problem = gitflow.check_commit(body.message)

        if problem:
            raise HTTPException(400, problem)

        with auth.git_auth(body.credentials):
            if body.branch:
                branch = self._branch_with_changes(repo, body)
            else:
                branch = repo.branch
                problem = gitflow.check_protected(branch, body.message)

                if problem:
                    raise HTTPException(400, problem)

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
                config = Config.from_toml(root / settings.CONFIG_FILE)
                auth.apply(config, body.credentials)
                ref = GitFlow(repo).open_pr(config=config)
                result["pull_request"] = {"number": ref.number, "url": ref.url}

        return result

    def _branch_with_changes(self, repo: Repository, body: CommitRequest) -> str:
        spec = body.branch

        with repo.stashed():
            try:
                branch = GitFlow(repo).start(
                    spec.kind, spec.code, spec.slug, push=False
                )
            except BranchError as e:
                raise HTTPException(400, str(e)) from e

        return branch.name
