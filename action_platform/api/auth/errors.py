from action_platform.core.exception import ActionPlatformError


class AuthError(ActionPlatformError):
    """Refused by the auth rules: `code` is the machine name (OAuth style), `status` the HTTP status it maps to."""

    def __init__(self, code: str, detail: str, status: int = 400) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status = status


class Unauthenticated(AuthError):
    def __init__(self, detail: str = "sign in first") -> None:
        super().__init__("unauthenticated", detail, 401)


class Forbidden(AuthError):
    def __init__(self, detail: str) -> None:
        super().__init__("forbidden", detail, 403)
