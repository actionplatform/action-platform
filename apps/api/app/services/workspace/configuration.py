from pathlib import Path

import tomllib

from action_platform.core.wiring import wired
from action_platform.core.flow import gitflow
from action_platform.core.flow.repository import Repository
from action_platform.core.flow.workflow import BranchError
from action_platform.core.scaffold.install import install
from action_platform.core.scaffold.templates import TemplateError
from action_platform.settings import settings
from app.core.shared import git_auth as auth
from app.repositories.registry import Registry
from app.schemas import CommitRequest, SourceSpec
from app.services.catalog import TemplateRepos
from app.services.workspace import Workspaces
from app.core.errors import Conflict, Invalid


def _same(a: str, b: str) -> bool:
    try:
        return tomllib.loads(a) == tomllib.loads(b)
    except tomllib.TOMLDecodeError:
        return False


class ConfigurationService:
    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    def _root(self, id: str) -> Path:
        return Workspaces(self.registry).checkout(id)[1]

    def _drafted(self, id: str, root: Path) -> list[str]:
        return self.registry.drafts.capture(id, root)

    def manifest(self, id: str) -> dict:
        """The configuration the platform keeps, rendered as platform.toml; whether the clone's file matches it."""
        root = self._root(id)
        content = self.registry.configs.render(id, root)
        file = root / settings.CONFIG_FILE
        mirrored = file.exists() and _same(file.read_text(), content)

        return {"content": content, "mirrored": mirrored}

    def write_manifest(self, id: str, content: str) -> dict:
        """Save to the platform — nothing in the repository changes until the mirror is exported."""
        try:
            data = tomllib.loads(content)
        except tomllib.TOMLDecodeError as e:
            raise Invalid(f"invalid TOML: {e}") from e

        self.registry.configs.set(id, data)

        return self.manifest(id)

    def export_manifest(self, id: str) -> dict:
        """Write platform.toml in the clone from what the platform keeps — a pending change to commit like any other."""
        root = self._root(id)
        self.registry.configs.export(id, root)
        self._drafted(id, root)

        return self.manifest(id)

    def set_cloud(self, id: str, target: str, source: SourceSpec | None = None) -> dict:
        repo, matrix = TemplateRepos.resolve(source)

        root = self._root(id)

        try:
            wired.scaffolder().apply_cloud(repo, matrix.cloud(target), root)
        except TemplateError as e:
            raise Invalid(str(e)) from e

        self._remember(id, root)
        self._drafted(id, root)

        return {"target": target}

    def _remember(self, id: str, root: Path) -> None:
        """An overlay wrote `[deploy]` or `[services]` into the clone's file; the platform's record takes them."""
        file = root / settings.CONFIG_FILE

        if not file.exists():
            return

        data = tomllib.loads(file.read_text())
        self.registry.configs.merge(
            id, root, deploy=data.get("deploy", {}), services=data.get("services", {})
        )

    def add_service(
        self, id: str, name: str, provider: str | None, source: SourceSpec | None = None
    ) -> dict:
        repo, matrix = TemplateRepos.resolve(source)
        service = next((s for s in matrix.services if s.name == name), None)

        if service is None:
            raise Invalid(f"unknown service: {name}")

        root = self._root(id)
        wired.scaffolder().apply_service(repo, service, root, provider=provider)
        self._remember(id, root)
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
                config = self.registry.configs.config(id, root)
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
