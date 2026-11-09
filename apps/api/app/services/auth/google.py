"""Sign in with Google: an OpenID Connect authorization-code round trip with PKCE, signed state, and accounts linked by Google's subject or verified email."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlencode

from sqlalchemy import select

from action_platform.core.exception import ProviderError
from action_platform.options import Env, secret
from app.core.auth.secrets import Secrets
from app.core.db.models import Account, Invitation, Session, User
from app.core.shared.http import HttpClient, http
from app.services.auth.base import AuthBase, new_id, now
from app.services.auth.errors import AuthError, Forbidden

GOOGLE = "google"
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ISSUERS = ("accounts.google.com", "https://accounts.google.com")
STATE_TTL = 10 * 60
CALLBACK_PATH = "/api/sign-in/google/callback"


@dataclass(frozen=True)
class GoogleConfig:
    """`AP_GOOGLE_CLIENT_ID` and `AP_GOOGLE_CLIENT_SECRET` (or `_FILE`): the OAuth client of a Google Cloud project."""

    client_id: str = ""
    client_secret: str = ""

    @classmethod
    def from_env(cls, env: Env) -> "GoogleConfig":
        return cls(
            client_id=env.get("AP_GOOGLE_CLIENT_ID", ""),
            client_secret=secret("AP_GOOGLE_CLIENT_SECRET", env=env),
        )

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)


@dataclass(frozen=True)
class GoogleStart:
    url: str
    verifier: str


@dataclass(frozen=True)
class GoogleProfile:
    subject: str
    email: str
    name: str
    image: Optional[str]


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _local(path: str) -> str:
    return (
        path
        if path.startswith("/") and not path.startswith(("//", "/\\"))
        else "/projects"
    )


def callback_url(origin: str) -> str:
    return f"{origin.rstrip('/')}{CALLBACK_PATH}"


class GoogleClient:
    """The two calls to Google: where to send the browser, and the code exchanged for the signed-in profile."""

    def __init__(
        self,
        config: GoogleConfig,
        secrets: Secrets,
        client: Optional[HttpClient] = None,
    ) -> None:
        self.config = config
        self.key = secrets.subkey("sign-in-state")
        self.http = client or http

    def start(self, origin: str, next_path: str) -> GoogleStart:
        verifier = _b64(secrets.token_bytes(32))
        challenge = _b64(hashlib.sha256(verifier.encode()).digest())
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": callback_url(origin),
            "response_type": "code",
            "scope": "openid email profile",
            "state": self._sign({"next": _local(next_path)}),
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }

        return GoogleStart(f"{AUTHORIZE_URL}?{urlencode(params)}", verifier)

    def finish(
        self, origin: str, code: str, state: str, verifier: str
    ) -> tuple[GoogleProfile, str]:
        """The verified profile and the path to return to; refused when the state is forged or stale, or Google does not vouch for the email."""
        payload = self._verify(state)

        if payload is None:
            raise AuthError("invalid_state", "the Google sign-in expired, start again")

        try:
            tokens = self.http.post_form(
                TOKEN_URL,
                {
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "code": code,
                    "code_verifier": verifier,
                    "grant_type": "authorization_code",
                    "redirect_uri": callback_url(origin),
                },
            )
        except ProviderError as e:
            raise AuthError(
                "google_refused", "Google did not accept the sign-in, start again", 400
            ) from e

        return self._profile(tokens.get("id_token")), payload.get("next") or "/projects"

    def _profile(self, id_token: Optional[str]) -> GoogleProfile:
        claims = self._claims(id_token)

        if (
            claims.get("aud") != self.config.client_id
            or claims.get("iss") not in ISSUERS
            or int(claims.get("exp", 0)) < time.time()
            or not claims.get("sub")
        ):
            raise AuthError(
                "invalid_token", "Google answered with an unusable identity"
            )

        if not claims.get("email") or claims.get("email_verified") is not True:
            raise AuthError(
                "unverified_email", "Google has not verified the email of this account"
            )

        email = str(claims["email"]).strip().lower()

        return GoogleProfile(
            subject=str(claims["sub"]),
            email=email,
            name=str(claims.get("name") or email.split("@", 1)[0]),
            image=claims.get("picture"),
        )

    @staticmethod
    def _claims(id_token: Optional[str]) -> dict[str, Any]:
        """The ID token's claims. It came straight from Google's token endpoint over TLS, which OpenID Connect accepts in place of checking its signature."""
        parts = (id_token or "").split(".")

        if len(parts) != 3:
            raise AuthError("invalid_token", "Google answered without an ID token")

        try:
            return json.loads(_unb64(parts[1]))
        except ValueError as e:
            raise AuthError(
                "invalid_token", "Google answered with an unreadable ID token"
            ) from e

    def _sign(self, data: dict[str, Any]) -> str:
        body = _b64(
            json.dumps(
                {**data, "nonce": secrets.token_hex(8), "ts": int(time.time())},
                separators=(",", ":"),
            ).encode()
        )

        return f"{body}.{self._mac(body)}"

    def _verify(self, raw: str) -> Optional[dict[str, Any]]:
        body, dot, mac = (raw or "").rpartition(".")

        if not dot or not hmac.compare_digest(mac, self._mac(body)):
            return None

        try:
            data = json.loads(_unb64(body))
        except ValueError:
            return None

        if time.time() - data.get("ts", 0) > STATE_TTL:
            return None

        return data

    def _mac(self, body: str) -> str:
        return _b64(hmac.new(self.key, body.encode(), "sha256").digest())


class GoogleAccounts(AuthBase):
    def sign_in_with_google(
        self,
        profile: GoogleProfile,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> tuple[User, Session]:
        """The user Google vouches for: the one already linked, the one with that email (linked now), or a new one when an owner invited that email; sign-up stays closed otherwise."""
        user = self._linked(profile.subject) or self.db.scalar(
            select(User).where(User.email == profile.email)
        )

        if user is None:
            user = self._invited_user(profile)

        if self._linked(profile.subject) is None:
            self._link(user, profile)

        if not user.email_verified or (profile.image and not user.image):
            user.email_verified = True
            user.image = user.image or profile.image
            user.updated_at = now()

        self.db.flush()

        return user, self.open_session(user, ip, user_agent)

    def _linked(self, subject: str) -> Optional[User]:
        account = self.db.scalar(
            select(Account).where(
                Account.provider_id == GOOGLE, Account.account_id == subject
            )
        )

        return self.db.get(User, account.user_id) if account else None

    def _invited_user(self, profile: GoogleProfile) -> User:
        if self.user_count() == 0:
            raise Forbidden(
                "finish the setup first: create the first account with a password"
            )

        invited = self.db.scalar(
            select(Invitation).where(
                Invitation.email == profile.email,
                Invitation.status == "pending",
                Invitation.expires_at > now(),
            )
        )

        if invited is None:
            raise Forbidden(
                f"no account for {profile.email}: an owner has to invite you"
            )

        moment = now()
        user = User(
            id=new_id(),
            name=profile.name,
            email=profile.email,
            email_verified=True,
            image=profile.image,
            created_at=moment,
            updated_at=moment,
        )
        self.db.add(user)
        self.db.flush()

        return user

    def _link(self, user: User, profile: GoogleProfile) -> None:
        moment = now()
        self.db.add(
            Account(
                id=new_id(),
                account_id=profile.subject,
                provider_id=GOOGLE,
                user_id=user.id,
                created_at=moment,
                updated_at=moment,
            )
        )

    def pending_invitation_of(self, email: str) -> Optional[str]:
        return self.db.scalar(
            select(Invitation.id).where(
                Invitation.email == email,
                Invitation.status == "pending",
                Invitation.expires_at > now(),
            )
        )
