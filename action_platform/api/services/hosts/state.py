"""Signed, short-lived state carried through the OAuth round trip."""

from __future__ import annotations

import base64
import hmac
import json
import secrets
import time
from typing import Any, Optional

from action_platform.api.auth.secrets import Secrets

STATE_TTL = 10 * 60


class OAuthState:
    """Signed, short-lived state for the OAuth round trip: organization, where to return, who started it."""

    def __init__(self, secrets: Secrets) -> None:
        self.key = secrets.subkey("oauth-state")

    def sign(self, organization_id: str, return_to: str, user_id: Optional[str]) -> str:
        payload = self._encode(
            json.dumps(
                {
                    "orgId": organization_id,
                    "returnTo": return_to,
                    "userId": user_id,
                    "nonce": secrets.token_hex(8),
                    "ts": int(time.time() * 1000),
                },
                separators=(",", ":"),
            ).encode()
        )

        return f"{payload}.{self._mac(payload)}"

    def verify(
        self, raw: Optional[str], user_id: Optional[str]
    ) -> Optional[dict[str, Any]]:
        if not raw or "." not in raw:
            return None

        payload, _, mac = raw.rpartition(".")

        if not hmac.compare_digest(mac, self._mac(payload)):
            return None

        try:
            state = json.loads(self._decode(payload))
        except ValueError:
            return None

        if time.time() * 1000 - state.get("ts", 0) > STATE_TTL * 1000:
            return None

        if state.get("userId") and state["userId"] != user_id:
            return None

        return state

    def _mac(self, payload: str) -> str:
        return self._encode(hmac.new(self.key, payload.encode(), "sha256").digest())

    @staticmethod
    def _encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    @staticmethod
    def _decode(data: str) -> bytes:
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
