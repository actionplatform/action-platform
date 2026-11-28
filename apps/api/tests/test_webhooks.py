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

    def app_secret(self, secret: str) -> None:
        from app.core.db.models import OAuthApp

        with self.app.state.db.session() as s:
            s.add(
                OAuthApp(
                    provider="github",
                    client_id="Iv1",
                    client_secret_encrypted=self.app.state.sealer.seal("sec"),
                    slug="ap",
                    webhook_secret_encrypted=self.app.state.sealer.seal(secret),
                )
            )

    def test_the_github_app_delivery_finds_the_app_by_repository(self):
        from app.core.db.models import Job

        registry_id = self.register()
        self.github_host()
        self.point_registry_at(registry_id, "https://github.com/acme/demo.git")
        self.app_secret("hook")

        bad = self.client.post(
            "/api/v1/webhooks/github-app",
            content=b"{}",
            headers={"x-github-event": "push", "x-hub-signature-256": "sha256=nope"},
        )
        self.assertEqual(bad.status_code, 403)

        ok = self.send(
            "github-app",
            "hook",
            "push",
            {"repository": {"full_name": "acme/demo"}, "installation": {"id": 7}},
        )
        self.assertEqual(ok.status_code, 202, ok.text)
        self.assertEqual(len(ok.json()["queued"]), 1)

        with self.app.state.db.session() as s:
            job = s.get(Job, ok.json()["queued"][0])
            self.assertEqual((job.kind, job.app_id), ("sync", "a1"))
            self.assertEqual(job.organization_id, self.org["id"])

        self.assertEqual(
            self.send(
                "github-app", "hook", "push", {"repository": {"full_name": "acme/x"}}
            ).json()["queued"],
            [],
        )

    def test_the_github_app_skips_apps_on_another_host(self):
        registry_id = self.register()
        self.point_registry_at(registry_id, "https://github.com/acme/demo.git")
        self.app_secret("hook")

        res = self.send(
            "github-app", "hook", "push", {"repository": {"full_name": "acme/demo"}}
        )
        self.assertEqual(res.status_code, 202, res.text)
        self.assertEqual(res.json()["queued"], [])

    def test_a_github_app_without_a_webhook_secret_takes_nothing(self):
        res = self.client.post(
            "/api/v1/webhooks/github-app",
            content=b"{}",
            headers={"x-github-event": "push", "x-hub-signature-256": "sha256=x"},
        )
        self.assertEqual(res.status_code, 404)

    def test_a_host_without_a_secret_takes_nothing(self):
        self.register()
        host_id = self.github_host()
        res = self.client.post(
            f"/api/v1/webhooks/{host_id}",
            content=b"{}",
            headers={"x-github-event": "push", "x-hub-signature-256": "sha256=x"},
        )
        self.assertEqual(res.status_code, 404)

    def test_the_github_app_secret_is_generated_once_and_verifies_deliveries(self):
        registry_id = self.register()
        self.github_host()
        self.point_registry_at(registry_id, "https://github.com/acme/demo.git")
        self.client.put(
            "/api/v1/oauth/apps/github",
            json={"client_id": "Iv1", "client_secret": "sec"},
            headers=self.h(),
        )

        info = self.client.get(
            "/api/v1/oauth/apps/github/webhook", headers=self.h()
        ).json()
        self.assertFalse(info["configured"])
        self.assertTrue(info["url"].endswith("/api/webhooks/github-app"))

        secret = self.client.post(
            "/api/v1/oauth/apps/github/webhook", headers=self.h()
        ).json()["secret"]
        self.assertTrue(
            self.client.get(
                "/api/v1/oauth/apps/github/webhook", headers=self.h()
            ).json()["configured"]
        )

        ok = self.send(
            "github-app", secret, "push", {"repository": {"full_name": "acme/demo"}}
        )
        self.assertEqual(ok.status_code, 202, ok.text)
        self.assertEqual(len(ok.json()["queued"]), 1)

    def test_no_github_app_no_webhook_secret(self):
        res = self.client.post("/api/v1/oauth/apps/github/webhook", headers=self.h())
        self.assertEqual(res.status_code, 400, res.text)
