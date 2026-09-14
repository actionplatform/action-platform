import re
from typing import Any, Optional

from action_platform.api.access.rules import Rule
from action_platform.api.db.models import App, Organization
from action_platform.api.services.directory import DirectoryService

SOURCE_BODY = re.compile(r"^apps/(init|[^/]+/(cloud|services))$")


def enrich(
    directory: DirectoryService,
    organization: Optional[Organization],
    app: Optional[App],
    path: str,
    parsed: dict[str, Any],
    rule: Rule,
) -> dict[str, Any]:
    """What the workspace routes need from the database: template sources by name, the source host's credentials and the organization's commit identity."""

    if organization is None:
        return parsed

    if SOURCE_BODY.match(path) and isinstance(parsed.get("source"), str):
        parsed["source"] = directory.source_spec_by_name(
            organization.id, parsed["source"]
        )

    if rule.credentials and not parsed.get("credentials"):
        parsed["credentials"] = credentials_for(directory, organization, app, parsed)

    return parsed


def credentials_for(
    directory: DirectoryService,
    organization: Organization,
    app: Optional[App],
    parsed: dict[str, Any],
) -> dict[str, Any]:
    if app is not None:
        host_id = app.source_host_id
    elif isinstance(parsed.get("url"), str):
        host_id = directory.host_id_for_url(organization.id, parsed["url"])
    else:
        host_id = None

    creds = directory.credentials_for(organization.id, host_id)
    name, email = directory.git_author_of(organization.id)

    return {
        **(creds.as_dict() if creds else {}),
        "author_name": name,
        "author_email": email,
    }
