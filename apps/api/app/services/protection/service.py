"""Git-flow on the code host for one app: whether it is enforced, the policy its repository gets, what the host enforces now, and the events that changed it."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session as DbSession

from action_platform.abc.branch_protection import BranchProtection
from action_platform.core.exception import ActionPlatformError, ConfigError
from action_platform.core.flow.protection import (
    Identity,
    Policy,
    ProtectionSpec,
    ProtectionState,
    declared_checks,
    protected_branches,
)
from action_platform.core.flow.repository import Repository
from action_platform.providers.protection import (
    PROTECTION_KINDS,
    build_branch_protection,
)
from app.core.auth.crypto import Sealer
from app.core.db.models import App
from app.core.errors import Invalid
from app.repositories.protection import ProtectionStore
from app.schemas.common import SourceCredentials
from app.services.integrations.hosts.directory import IntegrationsDirectory
from app.services.integrations.hosts.github_app_key import GithubAppKey
from app.services.workspace.app_context import AppContext
from app.services.workspace.checkout import Workspaces
from app.services.workspace.git_auth import git_auth
from app.services.workspace.state import GitStateService

GIT_ERRORS = (ActionPlatformError, subprocess.CalledProcessError, OSError)
CI_FILES = (".github/workflows", ".gitlab-ci.yml", "bitbucket-pipelines.yml")
NO_GITHUB_KEY = (
    "the platform cannot push as its GitHub App: set AP_GITHUB_APP_ID and "
    "AP_GITHUB_APP_PRIVATE_KEY (the app's private key) so release commits still "
    "land on a protected branch; nothing was applied"
)

Build = Callable[..., BranchProtection]


class ProtectionService:
    def __init__(
        self,
        db: DbSession,
        sealer: Optional[Sealer],
        context: AppContext,
        github_app: Optional[GithubAppKey] = None,
        build: Optional[Build] = None,
    ) -> None:
        self.db = db
        self.store = ProtectionStore(db)
        self.directory = IntegrationsDirectory(db, sealer)
        self.context = context
        self.github_app = github_app
        self.build = build or build_branch_protection

    @classmethod
    def from_env(
        cls, db: DbSession, sealer: Optional[Sealer], context: AppContext
    ) -> "ProtectionService":
        return cls(db, sealer, context, GithubAppKey.from_env(os.environ))

    def spec(self, app: App) -> ProtectionSpec:
        try:
            return self.context.config_of(app).protection
        except ConfigError:
            return ProtectionSpec()

    def enforced(self, organization_id: str, app: App) -> bool:
        return self.spec(app).resolved(self.store.default(organization_id))

    def view(self, organization_id: str, app: App) -> dict[str, Any]:
        spec = self.spec(app)
        default = self.store.default(organization_id)
        row = self.store.of(app.id)

        return {
            "enforce": spec.resolved(default),
            "source": "organization" if spec.enforce is None else "app",
            "organization_default": default,
            "branches": list(spec.branches),
            "state": self.store.state(app.id),
            "checked_at": row.checked_at if row else None,
            "applied_at": row.applied_at if row else None,
        }

    def set_enforce(
        self,
        organization_id: str,
        app: App,
        enforce: Optional[bool],
        actor: Optional[str] = None,
    ) -> dict[str, Any]:
        data = dict(self.context.configs.get(app.registry_id) or {})
        gitflow = dict(data.get("gitflow") or {})
        table = dict(gitflow.get("protection") or {})

        if enforce is None:
            table.pop("enforce", None)
        else:
            table["enforce"] = enforce

        if table:
            gitflow["protection"] = table
        else:
            gitflow.pop("protection", None)

        if gitflow:
            data["gitflow"] = gitflow
        else:
            data.pop("gitflow", None)

        self.context.configs.set(app.registry_id, data)
        now_enforced = self.enforced(organization_id, app)
        self.store.record(
            app.id,
            "enabled" if now_enforced else "disabled",
            "Branch protection enforced"
            if now_enforced
            else "Branch protection no longer enforced",
            None
            if now_enforced
            else "the platform stops reapplying the rules; what the host has stays until removed there",
            actor,
        )

        return self.view(organization_id, app)

    def set_default(self, organization_id: str, enforce: bool) -> None:
        self.store.set_default(organization_id, enforce)

    def check(self, organization_id: str, app: App) -> ProtectionState:
        """What the host enforces now; stored for the pages."""
        provider, policy, reason = self.target(organization_id, app)
        state = self._read(provider, policy, reason, app)
        self.store.save(app.id, state.as_dict(), self.enforced(organization_id, app))

        return state

    def apply(
        self, organization_id: str, app: App, actor: Optional[str] = None
    ) -> ProtectionState:
        provider, policy, reason = self.target(organization_id, app)

        if reason is not None or provider is None or policy is None:
            state = ProtectionState(self._kind(organization_id, app)).refuse(
                reason or "nothing to apply"
            )
        else:
            state = provider.apply(policy)

        self.store.save(
            app.id, state.as_dict(), self.enforced(organization_id, app), applied=True
        )
        self._record_apply(app, state, actor)

        return state

    def reconcile(self, organization_id: str, app: App) -> Optional[ProtectionState]:
        """For an app whose rules are enforced: read the host, put the policy back when it drifted, and say so in the app's activity."""
        if not self.enforced(organization_id, app):
            return None

        current = self.check(organization_id, app)
        row = self.store.of(app.id)

        if row is None or row.applied_at is None:
            return self.apply(organization_id, app, "platform")

        if current.error is not None or not current.drift:
            return current

        self.store.record(
            app.id,
            "drift",
            "Branch protection changed on the host",
            "; ".join(current.drift),
            current.changed_by,
        )

        return self.apply(organization_id, app, "platform")

    def _record_apply(
        self, app: App, state: ProtectionState, actor: Optional[str]
    ) -> None:
        if state.error is not None:
            self.store.record(
                app.id, "failed", "Branch protection not applied", state.error, actor
            )

            return

        native = [r.rule for r in state.rules if r.mode == "native"]
        self.store.record(
            app.id,
            "applied",
            "Branch protection applied",
            f"{', '.join(state.branches)}: {len(native)} rule(s) enforced by {state.host}",
            actor,
        )

    def _kind(self, organization_id: str, app: App) -> str:
        creds = self.credentials(organization_id, app)

        return creds.kind if creds and creds.kind else ""

    def _read(
        self,
        provider: Optional[BranchProtection],
        policy: Optional[Policy],
        reason: Optional[str],
        app: App,
    ) -> ProtectionState:
        if provider is None or policy is None:
            return ProtectionState("").refuse(reason or "no code host")

        if reason is not None:
            state = provider.status(policy)
            state.error = state.error or reason

            return state

        return provider.status(policy)

    def credentials(
        self, organization_id: str, app: App
    ) -> Optional[SourceCredentials]:
        creds = self.directory.credentials_for(
            organization_id, self.directory.app_host_id(organization_id, app)
        )

        return SourceCredentials(**creds.as_dict()) if creds else None

    def target(
        self, organization_id: str, app: App
    ) -> tuple[Optional[BranchProtection], Optional[Policy], Optional[str]]:
        """The host's provider, the policy for this repository, and why nothing may be applied (None when it may)."""
        creds = self.credentials(organization_id, app)

        if creds is None or not creds.token:
            return None, None, "no code host is connected for this app"

        if creds.kind not in PROTECTION_KINDS:
            raise Invalid(
                f"{creds.kind or 'this host'} has no branch protection the platform can apply"
            )

        repo = self.context.repo_of(app)

        if not repo:
            return None, None, "the app has no repository on the host"

        spec = self.spec(app)

        with git_auth(creds):
            branches, declared = self._repository(app, spec, creds.kind)

        identity, reason = (
            self._github_identity(repo) if creds.kind == "github" else (None, None)
        )
        provider = self.build(
            creds.kind,
            repo,
            creds.token,
            base_url=creds.base_url,
            username=creds.username,
            app=identity,
        )
        extra = self._ci_contexts(organization_id, app, provider)
        policy = Policy(
            branches=branches,
            checks=tuple(dict.fromkeys(declared + extra)),
            identity=identity if creds.kind == "github" else provider.identity(),
        )

        return provider, policy, reason

    def _github_identity(self, repo: str) -> tuple[Optional[Identity], Optional[str]]:
        if self.github_app is None:
            return None, NO_GITHUB_KEY

        try:
            self.github_app.installation(repo)
        except ActionPlatformError as e:
            return None, f"the platform's GitHub App is not installed on {repo}: {e}"

        return (
            Identity(
                "github_app",
                self.github_app.app_id,
                self.github_app.slug or self.github_app.app_id,
            ),
            None,
        )

    def _repository(
        self, app: App, spec: ProtectionSpec, kind: str
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        try:
            names = [
                b["name"]
                for b in GitStateService(self.context.registry).branches(
                    app.registry_id
                )
            ]
            entry, root = Workspaces(self.context.registry).checkout(app.registry_id)
        except GIT_ERRORS:
            return spec.branches, ()

        branches = protected_branches(spec, names)
        source = (
            entry.default_branch
            if entry.default_branch in branches
            else (branches[0] if branches else "")
        )

        if not source:
            return branches, ()

        return branches, ci_checks(root, source, kind)

    def _ci_contexts(
        self, organization_id: str, app: App, provider: BranchProtection
    ) -> tuple[str, ...]:
        if not app.ci_host_id:
            return ()

        host = self.directory.ci_host(organization_id, app.ci_host_id)

        if host is None or not host.base_url:
            return ()

        return provider.contexts(host.base_url)


def ci_checks(root: Path, branch: str, kind: str) -> tuple[str, ...]:
    """The platform checks declared by the CI files on `branch` of the clone, whatever is checked out."""
    repo = Repository(root)
    ref = f"origin/{branch}"

    try:
        listed = repo.run(["ls-tree", "-r", "--name-only", ref, "--", *CI_FILES])
    except GIT_ERRORS:
        return ()

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        for name in listed.splitlines():
            if not name or ".." in Path(name).parts:
                continue

            target = base / name
            target.parent.mkdir(parents=True, exist_ok=True)

            try:
                target.write_text(repo.run(["show", f"{ref}:{name}"]))
            except GIT_ERRORS:
                continue

        return declared_checks(base, kind)
