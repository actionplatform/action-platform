"""The organization's GitHub App acting as itself: a JWT signed with the private key kept when the app was created from the manifest, traded for an installation token on one repository."""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from action_platform.core.exception import ProviderError
from app.core.shared.credentials import AppKey
from app.core.shared.http import http

API = "https://api.github.com"
VERSION = "2022-11-28"
SETTINGS = "/settings"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


@dataclass(frozen=True)
class Fix:
    """The page that removes what stops the platform from acting as its GitHub App on a repository."""

    label: str
    url: str

    def as_dict(self) -> dict[str, str]:
        return {"label": self.label, "url": self.url}


@dataclass(frozen=True)
class Installation:
    id: str
    account: str
    organization: bool
    permissions: dict[str, str] = field(default_factory=dict)

    @property
    def review_url(self) -> str:
        if self.organization:
            return f"https://github.com/organizations/{self.account}/settings/installations/{self.id}"

        return f"https://github.com/settings/installations/{self.id}"

    def missing(self, needs: dict[str, str]) -> list[tuple[str, str, str]]:
        return [
            (name, level, self.permissions.get(name, "none"))
            for name, level in needs.items()
            if self.permissions.get(name) != level
        ]


@dataclass(frozen=True)
class GithubApp:
    app_id: str
    private_key: str
    slug: str = ""

    @classmethod
    def of(cls, key: AppKey) -> "GithubApp":
        return cls(key.app_id, key.private_key, key.slug or "")

    @property
    def name(self) -> str:
        return self.slug or self.app_id

    @property
    def install_url(self) -> str:
        if not self.slug:
            return SETTINGS

        return f"https://github.com/apps/{self.slug}/installations/new"

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
                "the GitHub App's stored private key cannot be read"
            ) from e

        signature = key.sign(body, padding.PKCS1v15(), hashes.SHA256())

        return f"{body.decode()}.{_b64(signature)}"

    def _headers(self) -> dict[str, str]:
        return {
            "authorization": f"Bearer {self.jwt()}",
            "accept": "application/vnd.github+json",
            "x-github-api-version": VERSION,
        }

    def installation(self, repo: str) -> Optional[Installation]:
        """The app's installation that reaches `repo`; None when it is not installed there."""
        owner, _, name = repo.partition("/")

        try:
            data = http.get_json(
                f"{API}/repos/{quote(owner, safe='')}/{quote(name, safe='')}/installation",
                self._headers(),
            )
        except ProviderError as e:
            if str(e).startswith("404 "):
                return None

            raise

        account = data.get("account") or {}

        return Installation(
            str(data["id"]),
            account.get("login") or owner,
            account.get("type") == "Organization",
            dict(data.get("permissions") or {}),
        )

    def token(self, repo: str, installation: Optional[Installation] = None) -> str:
        """An installation token for `repo` alone, valid for an hour."""
        found = installation or self.installation(repo)

        if found is None:
            raise ProviderError(
                f"the GitHub App {self.name} is not installed on {repo}"
            )

        data = http.post_json(
            f"{API}/app/installations/{found.id}/access_tokens",
            {"repositories": [repo.partition("/")[2]]},
            self._headers(),
        )

        if not data.get("token"):
            raise ProviderError("GitHub issued no installation token")

        return data["token"]
