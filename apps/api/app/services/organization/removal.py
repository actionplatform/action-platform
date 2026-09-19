"""An organization leaves the platform: its projects and apps first (repositories on the host when asked), then everything the organization owned, then the row — by an owner who typed its slug."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session as DbSession

from app.core.auth.crypto import Sealer
from app.core.db.models import (
    ApiToken,
    ApiTokenClient,
    CiHost,
    Invitation,
    Job,
    JobLog,
    Member,
    Organization,
    OrganizationSetting,
    PluginOption,
    Session,
    SourceHost,
    Team,
    TeamMember,
    TemplateSource,
)
from app.core.errors import Forbidden, Invalid
from app.repositories.workspace.registry import Registry
from app.services.projects import ProjectService
from app.services.projects.apps import AppService
from app.services.projects.organization_import.directory import ImportDirectory


class OrganizationRemoval:
    def __init__(
        self, db: DbSession, sealer: Optional[Sealer], registry: Registry
    ) -> None:
        self.db = db
        self.sealer = sealer
        self.registry = registry
        self.directory = ImportDirectory(db, sealer)

    def check(
        self, organization: Organization, user_id: str, confirm: Optional[str]
    ) -> None:
        if self.directory.role_in(user_id, organization.id) != "owner":
            raise Forbidden("only an owner can delete the organization")

        if (confirm or "").strip() != organization.slug:
            raise Invalid(
                f"type the organization's slug ({organization.slug}) to confirm"
            )

    def delete(
        self,
        organization: Organization,
        user_id: str,
        confirm: Optional[str],
        repositories: bool,
    ) -> dict:
        self.check(organization, user_id, confirm)
        removed: list[str] = []
        deleted: list[str] = []
        projects = ProjectService(self.directory, AppService(self.registry))

        for project in self.directory.projects_of(organization.id):
            registry_ids, repos = projects.delete(organization, project, repositories)
            removed.extend(registry_ids)
            deleted.extend(repos)

        self._forget_rows(organization.id)
        self.db.delete(organization)
        self.db.flush()

        return {
            "organization": organization.slug,
            "removed": removed,
            "repositories": deleted,
        }

    def _forget_rows(self, organization_id: str) -> None:
        job_ids = list(
            self.db.scalars(
                select(Job.id).where(Job.organization_id == organization_id)
            )
        )

        if job_ids:
            self.db.execute(delete(JobLog).where(JobLog.job_id.in_(job_ids)))
            self.db.execute(delete(Job).where(Job.id.in_(job_ids)))

        token_ids = list(
            self.db.scalars(
                select(ApiToken.id).where(ApiToken.organization_id == organization_id)
            )
        )

        if token_ids:
            self.db.execute(
                delete(ApiTokenClient).where(ApiTokenClient.token_id.in_(token_ids))
            )
            self.db.execute(delete(ApiToken).where(ApiToken.id.in_(token_ids)))

        team_ids = list(
            self.db.scalars(
                select(Team.id).where(Team.organization_id == organization_id)
            )
        )

        if team_ids:
            self.db.execute(delete(TeamMember).where(TeamMember.team_id.in_(team_ids)))
            self.db.execute(delete(Team).where(Team.id.in_(team_ids)))

        for model in (
            Invitation,
            Member,
            SourceHost,
            CiHost,
            TemplateSource,
            PluginOption,
            OrganizationSetting,
        ):
            self.db.execute(
                delete(model).where(model.organization_id == organization_id)
            )

        self.db.execute(
            update(Session)
            .where(Session.active_organization_id == organization_id)
            .values(active_organization_id=None)
        )
