"""The platform as an OIDC issuer: discovery, JWKS, and tokens that verify against the published key."""

from __future__ import annotations

import base64
import json

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.services.identity import IdentityIssuer, subject_for
from tests.test_access import GateCase


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class IdentityTest(GateCase):
    def test_discovery_and_jwks_are_open(self):
        conf = self.client.get("/.well-known/openid-configuration")

        self.assertEqual(conf.status_code, 200, conf.text)
        self.assertTrue(conf.json()["issuer"])
        self.assertTrue(conf.json()["jwks_uri"].endswith("/.well-known/jwks.json"))

        jwks = self.client.get("/.well-known/jwks.json").json()

        self.assertEqual(jwks["keys"][0]["alg"], "RS256")
        self.assertEqual(jwks["keys"][0]["kty"], "RSA")

        again = self.client.get("/.well-known/jwks.json").json()

        self.assertEqual(again["keys"][0]["kid"], jwks["keys"][0]["kid"])

    def test_token_verifies_with_the_published_key_and_says_who(self):
        res = self.client.post(
            "/api/v1/identity/token",
            json={"audience": "sts.amazonaws.com"},
            headers=self.h(),
        )

        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        head, payload, signature = body["token"].split(".")
        claims = json.loads(_b64d(payload))

        self.assertEqual(claims["aud"], "sts.amazonaws.com")
        self.assertEqual(claims["sub"], body["subject"])
        self.assertTrue(claims["sub"].startswith("org:"))
        self.assertEqual(claims["iss"], body["issuer"])
        self.assertEqual(claims["exp"] - claims["iat"], 300)

        issuer = IdentityIssuer(
            self.app.state.db, self.app.state.sealer, body["issuer"]
        )
        public = serialization.load_pem_public_key(issuer.key().public_pem.encode())
        public.verify(
            _b64d(signature),
            f"{head}.{payload}".encode(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

    def test_subject_shape(self):
        self.assertEqual(
            subject_for("acme", "shop", "orders"), "org:acme:project:shop:app:orders"
        )
        self.assertEqual(subject_for("acme", None, None), "org:acme")
