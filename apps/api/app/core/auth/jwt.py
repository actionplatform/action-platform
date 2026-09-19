import base64
import hashlib
import hmac
import json
import time
from typing import Any

HEADER = {"alg": "HS256", "typ": "JWT"}


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def encode(claims: dict[str, Any], key: bytes) -> str:
    body = f"{_b64(json.dumps(HEADER, separators=(',', ':')).encode())}.{_b64(json.dumps(claims, separators=(',', ':')).encode())}"

    return f"{body}.{_b64(hmac.new(key, body.encode(), hashlib.sha256).digest())}"


def decode(token: str, key: bytes, issuer: str, audience: str) -> dict[str, Any] | None:
    parts = token.split(".")

    if len(parts) != 3:
        return None

    body = f"{parts[0]}.{parts[1]}"

    try:
        expected = hmac.new(key, body.encode(), hashlib.sha256).digest()

        if not hmac.compare_digest(_unb64(parts[2]), expected):
            return None

        header = json.loads(_unb64(parts[0]))
        claims = json.loads(_unb64(parts[1]))
    except (ValueError, TypeError):
        return None

    if header.get("typ") not in (None, "JWT"):
        return None

    if header.get("alg") != "HS256":
        return None

    if claims.get("iss") != issuer or claims.get("aud") != audience:
        return None

    if isinstance(claims.get("nbf"), (int, float)) and claims["nbf"] > time.time() + 10:
        return None

    if not isinstance(claims.get("exp"), (int, float)) or claims["exp"] <= time.time():
        return None

    return claims


def looks_like_jwt(token: str) -> bool:
    return token.count(".") == 2
