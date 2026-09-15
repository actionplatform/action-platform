"""The platform as an OIDC issuer: one RSA key, a JWKS the clouds read, and short-lived tokens that say which organization, project and app a deploy runs for — what AWS, GCP or Azure trust instead of a stored access key."""

from __future__ import annotations

import base64
import json
import secrets
import time
from typing import Any, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from action_platform.core.exception import ActionPlatformError
from app.core.auth.crypto import Sealer
from app.core.db.database import Database
from app.core.db.models import SigningKey

TTL = 300


class IdentityError(ActionPlatformError):
    """No key material, no issuer url."""


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _int(value: int) -> str:
    return _b64(value.to_bytes((value.bit_length() + 7) // 8, "big"))


class IdentityIssuer:
    def __init__(
        self, database: Database, sealer: Optional[Sealer], issuer: str
    ) -> None:
        self.database = database
        self.sealer = sealer
        self.issuer = issuer.rstrip("/")

    def key(self) -> SigningKey:
        """The signing key, made and sealed on first use."""
        if self.sealer is None:
            raise IdentityError(
                "AP_AUTH_SECRET is not set: nothing to seal the signing key with"
            )

        with self.database.session() as s:
            row = s.query(SigningKey).order_by(SigningKey.created_at.desc()).first()

            if row is not None:
                return row

            private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            private_pem = private.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            ).decode()
            public_pem = (
                private.public_key()
                .public_bytes(
                    serialization.Encoding.PEM,
                    serialization.PublicFormat.SubjectPublicKeyInfo,
                )
                .decode()
            )
            row = SigningKey(
                kid=secrets.token_hex(8),
                private_sealed=self.sealer.seal(private_pem),
                public_pem=public_pem,
            )
            s.add(row)
            s.commit()
            s.refresh(row)

            return row

    def jwks(self) -> dict[str, Any]:
        row = self.key()
        public = serialization.load_pem_public_key(row.public_pem.encode())
        numbers = public.public_numbers()

        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": "RS256",
                    "kid": row.kid,
                    "n": _int(numbers.n),
                    "e": _int(numbers.e),
                }
            ]
        }

    def configuration(self) -> dict[str, Any]:
        if not self.issuer:
            raise IdentityError(
                "AP_PUBLIC_URL is not set: the issuer needs a public url"
            )

        return {
            "issuer": self.issuer,
            "jwks_uri": f"{self.issuer}/.well-known/jwks.json",
            "response_types_supported": ["id_token"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "claims_supported": [
                "iss",
                "sub",
                "aud",
                "exp",
                "iat",
                "nbf",
                "jti",
                "organization",
                "project",
                "app",
                "stage",
                "actor",
            ],
        }

    def mint(self, subject: str, audience: str, ttl: int = TTL, **claims: Any) -> str:
        """A token for `audience`, valid `ttl` seconds, about `subject` — `org:<slug>:project:<slug>:app:<slug>` for a deploy the platform runs."""
        if not self.issuer:
            raise IdentityError(
                "AP_PUBLIC_URL is not set: the issuer needs a public url"
            )

        row = self.key()
        private = serialization.load_pem_private_key(
            self.sealer.open(row.private_sealed).encode(), password=None
        )
        now = int(time.time())
        header = {"alg": "RS256", "typ": "JWT", "kid": row.kid}
        payload = {
            "iss": self.issuer,
            "sub": subject,
            "aud": audience,
            "iat": now,
            "nbf": now - 5,
            "exp": now + ttl,
            "jti": secrets.token_hex(16),
            **{k: v for k, v in claims.items() if v is not None},
        }
        signing_input = ".".join(
            _b64(json.dumps(part, separators=(",", ":")).encode())
            for part in (header, payload)
        )
        signature = private.sign(
            signing_input.encode(), padding.PKCS1v15(), hashes.SHA256()
        )

        return f"{signing_input}.{_b64(signature)}"


def subject_for(organization: str, project: Optional[str], app: Optional[str]) -> str:
    parts = [f"org:{organization}"]

    if project:
        parts.append(f"project:{project}")

    if app:
        parts.append(f"app:{app}")

    return ":".join(parts)
