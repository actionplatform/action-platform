"""The platform's GitHub App acting as itself: a JWT signed with the app's private key, traded for an installation token on one repository. What lets the platform be the only one that pushes to a protected branch."""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Any, Mapping, Optional
from urllib.parse import quote

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from action_platform.core.exception import ProviderError
from app.core.shared.http import http

API = "https://api.github.com"
VERSION = "2022-11-28"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


@dataclass(frozen=True)
class GithubAppKey:
    app_id: str
    private_key: str
    slug: str = ""

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Optional["GithubAppKey"]:
        app_id = (env.get("AP_GITHUB_APP_ID") or "").strip()
        key = (env.get("AP_GITHUB_APP_PRIVATE_KEY") or "").strip().replace("\\n", "\n")

        if not app_id or not key:
            return None

        return cls(app_id, key, (env.get("AP_GITHUB_APP_SLUG") or "").strip())

    def jwt(self, moment: Optional[float] = None) -> str:
        issued = int(moment if moment is not None else time.time()) - 60
        header = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
        claims = _b64(
            json.dumps(
                {"iat": issued, "exp": issued + 540, "iss": self.app_id}
            ).encode()
        )
        body = f"{header}.{claims}".encode()

        try:
            key = serialization.load_pem_private_key(self.private_key.encode(), None)
        except ValueError as e:
            raise ProviderError(
                "AP_GITHUB_APP_PRIVATE_KEY is not a PEM private key"
            ) from e

        signature = key.sign(body, padding.PKCS1v15(), hashes.SHA256())

        return f"{body.decode()}.{_b64(signature)}"

    def _headers(self) -> dict[str, str]:
        return {
            "authorization": f"Bearer {self.jwt()}",
            "accept": "application/vnd.github+json",
            "x-github-api-version": VERSION,
        }

    def app(self) -> dict[str, Any]:
        return http.get_json(f"{API}/app", self._headers())

    def installation(self, repo: str) -> dict[str, Any]:
        owner, _, name = repo.partition("/")

        return http.get_json(
            f"{API}/repos/{quote(owner, safe='')}/{quote(name, safe='')}/installation",
            self._headers(),
        )

    def token(self, repo: str) -> str:
        """An installation token for `repo` alone, valid for an hour."""
        installation = self.installation(repo)
        data = http.post_json(
            f"{API}/app/installations/{installation['id']}/access_tokens",
            {"repositories": [repo.partition("/")[2]]},
            self._headers(),
        )

        if not data.get("token"):
            raise ProviderError("GitHub issued no installation token")

        return data["token"]
