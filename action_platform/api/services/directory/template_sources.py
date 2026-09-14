"""Custom template repositories of an organization."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from action_platform.api.db.models import (
    TemplateSource,
)
from action_platform.api.services.common import new_id, now, slugify
from action_platform.api.services.directory.base import (
    GIT_URL,
    DirectoryBase,
    DirectoryError,
)


class TemplateSourcesReads(DirectoryBase):
    def template_sources_of(self, organization_id: str) -> list[TemplateSource]:
        return list(
            self.db.scalars(
                select(TemplateSource)
                .where(TemplateSource.organization_id == organization_id)
                .order_by(TemplateSource.created_at)
            )
        )

    def source_specs_of(self, organization_id: str) -> list[dict]:
        specs = []

        for row in self.template_sources_of(organization_id):
            credentials = self.credentials_for(organization_id, row.source_host_id)
            specs.append(
                {
                    "name": row.name,
                    "url": row.url,
                    "ref": row.ref,
                    "credentials": credentials.as_dict() if credentials else None,
                }
            )

        return specs

    def source_spec_by_name(
        self, organization_id: str, name: Optional[str]
    ) -> Optional[dict]:
        if not name or name == "official":
            return None

        spec = next(
            (s for s in self.source_specs_of(organization_id) if s["name"] == name),
            None,
        )

        if spec is None:
            raise DirectoryError(f"template source {name} not found")

        return spec


class TemplateSourcesWrites(TemplateSourcesReads):
    def add_template_source(
        self, organization_id: str, name: str, url: str, ref: str
    ) -> TemplateSource:
        name = slugify(name)
        url = url.strip()
        ref = ref.strip() or "main"

        if not name:
            raise DirectoryError("name is required")

        if name == "official":
            raise DirectoryError("official is reserved")

        if not GIT_URL.match(url):
            raise DirectoryError("enter a git url")

        if self.db.scalar(
            select(TemplateSource.id).where(
                TemplateSource.organization_id == organization_id,
                TemplateSource.name == name,
            )
        ):
            raise DirectoryError(f"a source named {name} already exists")

        row = TemplateSource(
            id=new_id(),
            organization_id=organization_id,
            name=name,
            url=url,
            ref=ref,
            source_host_id=self.host_id_for_url(organization_id, url),
            created_at=now(),
        )
        self.db.add(row)
        self.db.flush()

        return row

    def remove_template_source(self, organization_id: str, id: str) -> None:
        row = self.db.scalar(
            select(TemplateSource).where(
                TemplateSource.id == id,
                TemplateSource.organization_id == organization_id,
            )
        )

        if row is not None:
            self.db.delete(row)
            self.db.flush()
