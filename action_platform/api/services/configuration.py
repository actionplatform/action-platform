import tomllib
from pathlib import Path

from fastapi import HTTPException

from action_platform.api.core import credentials as auth
from action_platform.api.repositories.registry import Registry
from action_platform.api.schemas import CommitRequest, SourceSpec
from action_platform.api.services.catalog import resolve_repo
from action_platform.api.services.manifest import workspace_of
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
        return workspace_of(self.registry, id)[1]

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

        path = self._root(id) / settings.CONFIG_FILE
        path.write_text(content if content.endswith("\n") else content + "\n")

        return {"content": path.read_text()}

    def set_cloud(self, id: str, target: str, source: SourceSpec | None = None) -> dict:
        repo, matrix = resolve_repo(source)

        try:
            apply_cloud(repo, matrix.cloud(target), self._root(id))
        except TemplateError as e:
            raise HTTPException(400, str(e)) from e

        return {"target": target}

    def add_service(
        self, id: str, name: str, provider: str | None, source: SourceSpec | None = None
    ) -> dict:
        repo, matrix = resolve_repo(source)
        service = next((s for s in matrix.services if s.name == name), None)

        if service is None:
            raise HTTPException(400, f"unknown service: {name}")

        apply_service(repo, service, self._root(id), provider=provider)

        return {
            "name": name,
            "provider": provider or (service.providers[0] if service.providers else ""),
        }

    def changes(self, id: str) -> dict:
        files = Repository(self._root(id)).changed_files()

        return {"files": files, "clean": not files}

    def discard(self, id: str) -> dict:
        repo = Repository(self._root(id))
        repo.reset_hard()
        repo.clean()

        return {"clean": True, "files": []}

    def install_platform(
        self, id: str, type_: str, language: str | None, ci: str | None
    ) -> dict:
        entry = self.registry.get(id)
        root = Path(entry.path)

        if not root.is_dir():
            raise HTTPException(410, f"{root} no longer exists")

        plan = install(root, type_=type_, language=language, ci=ci, name=entry.name)

        return {"installed": plan.created}

    def commit(self, id: str, body: CommitRequest) -> dict:
        root = self._root(id)
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
            push = body.push or body.pull_request

            if push:
                repo.push_upstream(branch)

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
