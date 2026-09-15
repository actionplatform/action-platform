"""What every router pulls from the request: the caller and its organization, the services, the rows it works on."""

from app.api.dependencies.access import (
    allowed,
    get_caller,
    manageable,
    org_of,
    required_org,
    requested_org,
)
from app.api.dependencies.lookups import (
    app_of,
    host_row,
    imports_of,
    org_dict,
    project_of,
)
from app.api.dependencies.services import (
    get_app_service,
    get_auth,
    get_configuration,
    get_db,
    get_directory,
    get_flow,
    get_git_state,
    get_lifecycle,
    get_queue,
    get_state_signer,
    get_writes,
)

__all__ = [
    "allowed",
    "app_of",
    "get_app_service",
    "get_auth",
    "get_caller",
    "get_configuration",
    "get_db",
    "get_directory",
    "get_flow",
    "get_git_state",
    "get_lifecycle",
    "get_queue",
    "get_state_signer",
    "get_writes",
    "host_row",
    "imports_of",
    "manageable",
    "org_dict",
    "org_of",
    "project_of",
    "required_org",
    "requested_org",
]
