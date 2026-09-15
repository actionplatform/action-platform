"""The session cookie the web app carries, and how to read it from a Cookie header."""

from typing import Optional

NAME = "better-auth.session_token"
SECURE_NAME = f"__Secure-{NAME}"


class SessionCookie:
    @staticmethod
    def value(header: str) -> Optional[str]:
        for part in header.split(";"):
            name, _, value = part.strip().partition("=")

            if name in (NAME, SECURE_NAME) and value:
                return value

        return None
