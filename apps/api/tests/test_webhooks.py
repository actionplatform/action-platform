"""Deliveries from the code host: verified, matched to the app, turned into a sync job."""

from __future__ import annotations

import hashlib
import hmac
import json
import unittest

from tests.test_access import GateCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


@unittest.skipUnless(TestClient, "fastapi is not installed")
class WebhooksTest(GateCase):
    def github_host(self) -> str:
        from app.core.db.models import App, SourceHost

        with self.app.state.db.session() as s:
            s.add(
                SourceHost(
                    id="h1",
                    organization_id=self.org["id"],
                    kind="github",
                    name="GitHub",
                    auth_kind="token",
                    token_encrypted=self.app.state.sealer.seal("ghp"),
                )
            )
            s.get(App, "a1").source_host_id = "h1"

        return "h1"

    def point_registry_at(self, registry_id: str, url: str) -> None:
        from app.core.db.models import RegistryEntry

        with self.app.state.db.session() as s:
            s.get(RegistryEntry, registry_id).url = url

    def send(self, host_id: str, secret: str, event: str, payload: dict):
        body = json.dumps(payload).encode()
        sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return self.client.post(
            f"/api/v1/webhooks/{host_id}",
            content=body,
            headers={
                "x-github-event": event,
                "x-hub-signature-256": sig,
                "content-type": "application/json",
            },
        )

    def test_secret_is_handed_out_once_and_deliveries_are_verified(self):
        from app.core.db.models import Job

        registry_id = self.register()
        host_id = self.github_host()
        self.point_registry_at(registry_id, "https://github.com/acme/demo.git")

        info = self.client.get(
            f"/api/v1/hosts/{host_id}/webhook", headers=self.h()
        ).json()
        self.assertFalse(info["configured"])
        self.assertTrue(info["url"].endswith(f"/api/webhooks/{host_id}"))

        secret = self.client.post(
            f"/api/v1/hosts/{host_id}/webhook", headers=self.h()
        ).json()["secret"]
        self.assertTrue(secret)
        self.assertTrue(
            self.client.get(
                f"/api/v1/hosts/{host_id}/webhook", headers=self.h()
            ).json()["configured"]
        )

        bad = self.client.post(
            f"/api/v1/webhooks/{host_id}",
            content=b"{}",
            headers={"x-github-event": "push", "x-hub-signature-256": "sha256=nope"},
        )
        self.assertEqual(bad.status_code, 403)

        ok = self.send(
            host_id,
            secret,
            "push",
            {"repository": {"full_name": "acme/demo"}, "ref": "refs/heads/main"},
        )
        self.assertEqual(ok.status_code, 202, ok.text)
        self.assertEqual(ok.json()["repo"], "acme/demo")
        self.assertEqual(len(ok.json()["queued"]), 1)

        with self.app.state.db.session() as s:
            job = s.get(Job, ok.json()["queued"][0])
            self.assertEqual(
                (job.kind, job.app_id, job.status), ("sync", "a1", "queued")
            )
            self.assertEqual(
                json.loads(job.payload)["webhook"], {"kind": "github", "event": "push"}
            )

        again = self.send(
            host_id, secret, "push", {"repository": {"full_name": "acme/demo"}}
        )
        self.assertEqual(again.json()["queued"], ok.json()["queued"])

    def test_unknown_events_and_other_repositories_are_ignored(self):
        registry_id = self.register()
        host_id = self.github_host()
        self.point_registry_at(registry_id, "https://github.com/acme/demo.git")
        secret = self.client.post(
            f"/api/v1/hosts/{host_id}/webhook", headers=self.h()
        ).json()["secret"]

        self.assertEqual(
            self.send(
                host_id,
                secret,
                "ping",
                {"zen": "x", "repository": {"full_name": "acme/demo"}},
            ).json()["queued"],
            [],
        )
        self.assertEqual(
            self.send(
                host_id, secret, "push", {"repository": {"full_name": "acme/other"}}
            ).json()["queued"],
            [],
        )

    def test_a_host_without_a_secret_takes_nothing(self):
        self.register()
        host_id = self.github_host()
        res = self.client.post(
            f"/api/v1/webhooks/{host_id}",
            content=b"{}",
            headers={"x-github-event": "push", "x-hub-signature-256": "sha256=x"},
        )
        self.assertEqual(res.status_code, 404)
