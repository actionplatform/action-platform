import base64
import hashlib
import hmac
import math
from urllib.parse import quote, unquote

from action_platform.core.exception import ConfigError

SALT = b"action-platform"
PURPOSES = ("api-token", "oauth-state", "source-host")


def hkdf(secret: bytes, salt: bytes, info: bytes, length: int) -> bytes:
    prk = hmac.new(salt, secret, hashlib.sha256).digest()
    blocks = b""
    previous = b""

    for i in range(1, math.ceil(length / 32) + 1):
        previous = hmac.new(prk, previous + info + bytes([i]), hashlib.sha256).digest()
        blocks += previous

    return blocks[:length]


class Secrets:
    """Everything derived from the one auth secret: HKDF subkeys per purpose and signed cookie values."""

    def __init__(self, secret: str) -> None:
        if not secret:
            raise ConfigError(
                "AP_AUTH_SECRET is empty: sessions and tokens cannot be signed"
            )

        self.secret = secret.encode()

    def subkey(self, purpose: str, length: int = 32) -> bytes:
        if purpose not in PURPOSES:
            raise ValueError(f"unknown key purpose {purpose}")

        return hkdf(self.secret, SALT, purpose.encode(), length)

    def signature(self, value: str) -> str:
        return base64.b64encode(
            hmac.new(self.secret, value.encode(), hashlib.sha256).digest()
        ).decode()

    def sign_cookie(self, value: str) -> str:
        return quote(f"{value}.{self.signature(value)}", safe="")

    def unsign_cookie(self, raw: str) -> str | None:
        decoded = unquote(raw or "")
        value, dot, signature = decoded.rpartition(".")

        if not dot or not value:
            return None

        return value if hmac.compare_digest(signature, self.signature(value)) else None
