"""The token a deploy target asks for while a job runs: signed by the platform about the app the job is for."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from action_platform.core.context import Context
from app.core.auth.crypto import Sealer
from app.core.db.database import Database
from app.core.db.models import App, Organization, Project
from app.services.deployments.env import DeployEnv
from app.services.identity.issuer import IdentityIssuer, subject_for


class AppIdentity:
    def __init__(
        self, database: Database, sealer: Optional[Sealer], issuer_url: str
    ) -> None:
        self.database = database
        self.sealer = sealer
        self.issuer_url = issuer_url

    def minter(
        self,
        organization: Optional[Organization],
        app: Optional[App],
        stage: Optional[str] = None,
    ) -> Optional[Callable[[str], str]]:
        """What `ctx.identity_token(audience)` calls — None when the platform cannot sign."""
        if organization is None or app is None or self.sealer is None:
            return None

        with self.database.session() as db:
            project = db.get(Project, app.project_id)

        project_slug = project.slug if project else None
        subject = subject_for(organization.slug, project_slug, app.name)
        issuer = IdentityIssuer(self.database, self.sealer, self.issuer_url)

        def mint(audience: str) -> str:
            return issuer.mint(
                subject,
                audience,
                organization=organization.slug,
                project=project_slug,
                app=app.name,
                stage=stage,
            )

        return mint


class TargetContexts:
    """What a deploy target is given when the platform asks it about an app outside a deploy — `verify`, `url`: the app's environment and an identity for the scope."""

    def __init__(
        self, database: Database, sealer: Optional[Sealer], issuer_url: str
    ) -> None:
        self.database = database
        self.sealer = sealer
        self.issuer_url = issuer_url

    def of(self, app: App, stage: Optional[str]) -> Context:
        with self.database.session() as db:
            project = db.get(Project, app.project_id)
            organization = (
                db.get(Organization, project.organization_id) if project else None
            )

        return Context(
            repo_root=Path.cwd(),
            stage=stage or "",
            env=DeployEnv(self.database, self.sealer).for_app(organization, app),
            identity=AppIdentity(self.database, self.sealer, self.issuer_url).minter(
                organization, app, stage
            ),
        )
