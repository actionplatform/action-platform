"""The front door of an organization import: which host, what it shows, and the job that runs it."""

from typing import Any, Optional


from action_platform.core.exception import ActionPlatformError
from app.core.db.models import Job, Organization
from app.core.shared.credentials import Credentials
from app.repositories.workspace.registry import Registry
from app.services.projects.organization_import.directory import ImportDirectory
from app.services.jobs import JobQueue
from app.services.projects.organization_import import client
from app.services.projects.organization_import.importer import OrganizationImport
from app.services.projects.organization_import.people import RoleMapping
from app.core.errors import Invalid, NotFound, Upstream

JOB_KIND = "import_organization"
IMPORTABLE = ("github", "gitlab", "bitbucket")


class ImportGateway:
    def __init__(
        self,
        writes: ImportDirectory,
        registry: Registry,
        queue: Optional[JobQueue] = None,
    ) -> None:
        self.writes = writes
        self.registry = registry
        self.queue = queue

    def credentials(self, org: Organization, host_id: str) -> Credentials:
        host = self.writes.host(org.id, host_id)

        if host is None:
            raise NotFound("host not found")

        if host.kind not in IMPORTABLE:
            raise Invalid(f"{host.kind} hosts cannot be imported")

        try:
            creds = self.writes.credentials_for(org.id, host_id)
        except ActionPlatformError as e:
            raise Invalid(f"{e}; reconnect the host") from e

        if creds is None:
            raise Invalid("this host has no credentials; reconnect it")

        return creds

    def organizations(
        self, org: Organization, host_id: str
    ) -> tuple[list[dict[str, Any]], Optional[str]]:
        """What the host's token can see, and on GitHub where to install the GitHub App when something is missing."""
        creds = self.credentials(org, host_id)
        github_app = self.writes.oauth_app("github") if creds.kind == "github" else None

        try:
            rows = client.directory_for(creds).organizations()
        except ActionPlatformError as e:
            raise Upstream(str(e)) from e

        install_url = (
            f"https://github.com/apps/{github_app.slug}/installations/select_target"
            if github_app and github_app.slug
            else None
        )

        return rows, install_url

    def preview(self, org: Organization, host_id: str, login: str) -> dict[str, Any]:
        creds = self.credentials(org, host_id)

        try:
            return OrganizationImport(self.writes, org.id, self.registry).preview(
                creds, login
            )
        except ActionPlatformError as e:
            raise Upstream(str(e)) from e

    def enqueue(
        self, org: Organization, inviter_id: str, request: dict[str, Any]
    ) -> Job:
        self.credentials(org, request["host_id"])

        if not any(
            request.get(k) for k in ("repositories", "projects", "teams", "people")
        ):
            raise Invalid("pick at least one repository, team or person")

        try:
            RoleMapping(
                request.get("role") or "developer",
                request.get("roles") or {},
                request.get("people_roles") or {},
            )
        except ActionPlatformError as e:
            raise Invalid(str(e)) from e

        return self.queue.enqueue(
            JOB_KIND,
            {**request, "organization_id": org.id, "inviter_id": inviter_id},
            organization_id=org.id,
        )
