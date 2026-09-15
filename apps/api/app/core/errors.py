"""What a service refuses, said in the domain's terms — the API boundary turns each into a status code; the worker and the tests see plain exceptions."""

from action_platform.core.exception import ActionPlatformError


class ServiceError(ActionPlatformError):
    """A refusal a caller can act on; `status` is what the API answers with, `code` a machine-readable name when a client should branch on it."""

    status = 400
    code: str | None = None


class Invalid(ServiceError):
    status = 400


class Forbidden(ServiceError):
    status = 403


class NotFound(ServiceError):
    status = 404


class Conflict(ServiceError):
    status = 409


class Gone(ServiceError):
    status = 410


class NeedsInstall(ServiceError):
    """A repository without platform.toml: call again with an install spec."""

    status = 422
    code = "needs_install"


class Upstream(ServiceError):
    """The code host or another remote system failed."""

    status = 502


class Refused(ServiceError):
    """A refusal with the status chosen at the point of refusal — what the /api/v1 gate says before a route runs."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail
