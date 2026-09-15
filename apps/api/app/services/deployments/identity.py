"""The token a deploy target asks for while a job runs: signed by the platform about the app the job is for."""

from __future__ import annotations

from typing import Callable, Optional

from app.core.auth.crypto import Sealer
from app.core.db.database import Database
from app.core.db.models import App, Organization, Project
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
        manages: bool = False,
    ) -> Optional[Callable[[str], str]]:
        """What `ctx.identity_token(audience)` calls — None when the platform cannot sign. `manages` puts `org.manage` in the token's scopes: the caller may register the app where it deploys."""
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
                scopes=["org.manage"] if manages else None,
            )

        return mint
