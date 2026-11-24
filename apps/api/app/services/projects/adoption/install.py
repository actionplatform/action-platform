"""The install job: per app, the installer's plan on a dry run, else a commit on `chore/<code>` and a pull request on its repository — each app on its own, so one failure never stops the others."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from action_platform.core.config import Config
from action_platform.core.exception import ActionPlatformError
from action_platform.core.files import CONFIG_FILE
from action_platform.core.flow.repository import Repository
from action_platform.core.flow.workflow import branch_name
from action_platform.core.scaffold.installer import Plan
from action_platform.core.scaffold.language import detect_language
from action_platform.core.wiring import wired
from app.core.db.database import Database
from app.core.errors import NotFound
from app.repositories.projects.adoption import AdoptionStore
from app.repositories.workspace.registry import Registry, check_workspace
from app.schemas import SourceCredentials
from app.services.projects.organization_import.directory import ImportDirectory
from app.services.workspace import git_auth as auth

log = logging.getLogger("action_platform.adoption")

MESSAGE = "chore(platform): install the platform"
PERMISSION = ("permission", "denied", "403", "forbidden", "not granted")


class NotAdoptable(ActionPlatformError):
    pass


@dataclass(frozen=True)
class InstallOptions:
    type: str = "web"
    ci: Optional[str] = None
    language: Optional[str] = None
    code: str = "platform"
    dry_run: bool = True

    @property
    def branch(self) -> str:
        return branch_name("chore", self.code)


@dataclass
class Target:
    id: str
    name: str
    registry_id: str
    credentials: Optional[SourceCredentials] = None
    pull_request: Optional[dict[str, Any]] = None
    problem: Optional[str] = None


def reason_of(error: BaseException) -> str:
    """One line a person can act on: archived and permission refusals named as such."""
    text = (
        error.stderr if isinstance(error, subprocess.CalledProcessError) else ""
    ) or str(error)
    line = next(
        (part.strip() for part in text.splitlines() if part.strip()),
        type(error).__name__,
    )[:300]
    lowered = text.lower()

    if "archived" in lowered:
        return "archived: the repository is read-only"

    if any(marker in lowered for marker in PERMISSION):
        return f"no permission: {line}"

    return line


def plan_view(plan: Plan, base: str, branch: str) -> dict[str, Any]:
    return {
        "type": plan.type,
        "language": plan.language,
        "ci": plan.ci,
        "detected_ci": list(plan.detected_ci),
        "created": list(plan.created),
        "kept": list(plan.skipped),
        "warnings": list(plan.warnings),
        "version": plan.version,
        "version_source": plan.version_source,
        "base": base,
        "branch": branch,
    }


class BulkInstall:
    def __init__(self, database: Database, sealer: Any, registry: Registry) -> None:
        self.database = database
        self.sealer = sealer
        self.registry = registry

    def run(
        self,
        organization_id: str,
        project_id: str,
        app_ids: list[str],
        options: InstallOptions,
    ) -> dict[str, Any]:
        results = [
            self._one(target, options)
            for target in self._targets(organization_id, project_id, app_ids, options)
        ]

        return {
            "dry_run": options.dry_run,
            "branch": options.branch,
            "apps": results,
            "opened": sum(
                1 for r in results if r["state"] == "pr_open" and not r["skipped"]
            ),
            "skipped": sum(1 for r in results if r["skipped"]),
            "failed": sum(1 for r in results if r["state"] == "failed"),
        }

    def _targets(
        self,
        organization_id: str,
        project_id: str,
        app_ids: list[str],
        options: InstallOptions,
    ) -> list[Target]:
        with self.database.session() as db:
            directory = ImportDirectory(db, self.sealer)
            project = directory.project(organization_id, project_id)

            if project is None:
                raise NotFound("project not found")

            wanted = set(app_ids)
            apps = [
                a for a in directory.apps_of(project.id) if not wanted or a.id in wanted
            ]
            name, email = directory.git_author_of(organization_id)
            adoption = AdoptionStore(db)
            known = adoption.of([a.id for a in apps])
            targets = []

            for app in apps:
                target = Target(app.id, app.name, app.registry_id)
                target.pull_request = adoption.open_pull_request(
                    app.id, known.get(app.id), options.branch
                )

                try:
                    creds = directory.credentials_for(
                        organization_id, app.source_host_id
                    )
                except ActionPlatformError as e:
                    target.problem = f"{e}; reconnect the host"
                    creds = None

                target.credentials = SourceCredentials(
                    **(creds.as_dict() if creds else {}),
                    author_name=name,
                    author_email=email,
                )
                targets.append(target)

            return targets

    def _one(self, target: Target, options: InstallOptions) -> dict[str, Any]:
        try:
            if target.problem:
                raise NotAdoptable(target.problem)

            outcome = self._install(target, options)
        except (ActionPlatformError, subprocess.CalledProcessError) as e:
            outcome = {"state": "failed", "reason": reason_of(e)}
        except Exception as e:
            log.exception("install on %s failed", target.name)
            outcome = {"state": "failed", "reason": reason_of(e)}

        result = {
            "app_id": target.id,
            "name": target.name,
            "skipped": False,
            "reason": None,
            "pull_request": None,
            "plan": None,
            **outcome,
        }
        log.info(
            "%s: %s%s",
            target.name,
            result["state"],
            f" ({result['reason']})" if result["reason"] else "",
        )
        self._record(target.id, result)

        return result

    def _install(self, target: Target, options: InstallOptions) -> dict[str, Any]:
        entry = self.registry.get(target.registry_id)

        if not entry.url:
            raise NotAdoptable("no remote to open a pull request on")

        with (
            auth.git_auth(target.credentials),
            tempfile.TemporaryDirectory(prefix="ap-install-") as tmp,
        ):
            root = Path(tmp) / "repository"
            repo = Repository.clone(entry.url, root)
            check_workspace(root)
            flow = wired.gitflow(repo)
            base = flow.resolve_base("chore")

            manifest = repo.attempt(["cat-file", "-e", f"origin/{base}:{CONFIG_FILE}"])

            if manifest.returncode == 0:
                return {"state": "installed", "skipped": True}

            if repo.remote_branch_exists(options.branch):
                if target.pull_request:
                    return {
                        "state": "pr_open",
                        "skipped": True,
                        "pull_request": target.pull_request,
                    }

                raise NotAdoptable(
                    f"branch {options.branch} already exists on the remote with no open install pull request; delete it or pick another code"
                )

            repo.checkout_tracking(base)
            language = options.language or detect_language(root)

            if not language:
                raise NotAdoptable(
                    "unknown language: pick one, or none to install without the quality config"
                )

            installer = wired.installer(
                root,
                type_=options.type,
                language=language,
                ci=options.ci,
                name=target.name,
            )

            if options.dry_run:
                return {
                    "state": "missing",
                    "plan": plan_view(installer.plan(), base, options.branch),
                }

            flow.start("chore", options.code, push=False)
            plan = installer.apply()
            repo.add_all()
            repo.commit(MESSAGE)
            config = auth.apply(
                Config.from_toml(root / CONFIG_FILE), target.credentials
            )
            ref = flow.open_pr(config=config)
            self._follow(target.registry_id, options.branch)

            return {
                "state": "pr_open",
                "pull_request": {"number": ref.number, "url": ref.url},
                "plan": plan_view(plan, base, options.branch),
            }

    def _follow(self, registry_id: str, branch: str) -> None:
        """The app moves to the install branch, as after a commit from its page: its pending install files are in the pull request now."""
        if self.registry.drafts is not None:
            self.registry.drafts.clear(registry_id)

        self.registry.set_branch(registry_id, branch)

    def _record(self, app_id: str, result: dict[str, Any]) -> None:
        plan = result.get("plan") or {}
        pull_request = result.get("pull_request") or {}

        with self.database.session() as db:
            AdoptionStore(db).record(
                app_id,
                keep=bool(result.get("skipped")),
                state=result["state"],
                reason=result.get("reason"),
                language=plan.get("language"),
                ci=plan.get("ci"),
                version=plan.get("version"),
                branch=plan.get("branch"),
                pull_request_number=pull_request.get("number"),
                pull_request_url=pull_request.get("url"),
            )
