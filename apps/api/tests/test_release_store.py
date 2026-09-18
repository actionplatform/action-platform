"""release as the platform's table: one row per tag, whatever named it, and deployments that reference it."""

from __future__ import annotations

import unittest
from datetime import datetime

from action_platform.core.context import DeployResult
from tests.test_access import GateCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


@unittest.skipUnless(TestClient, "fastapi is not installed")
class ReleaseStoreTest(GateCase):
    def setUp(self):
        super().setUp()
        self.registry_id = self.register()

    def store(self, db):
        from app.services.releases import ReleaseStore

        return ReleaseStore(db)

    def test_split_and_tag(self):
        from app.services.releases import split_tag, tag_of

        self.assertEqual(split_tag("v1.2.3"), ("", "1.2.3"))
        self.assertEqual(split_tag("web/v1.2.3"), ("web", "1.2.3"))
        self.assertEqual(split_tag("1.2.3"), ("", "1.2.3"))
        self.assertEqual(tag_of("", "1.2.3"), "v1.2.3")
        self.assertEqual(tag_of("api", "0.22.0"), "api/v0.22.0")

    def test_git_creates_a_host_enriches_git_never_downgrades(self):
        with self.app.state.db.session() as s:
            store = self.store(s)
            row = store.ensure("a1", "v1.0.0", "git", sha="abc")
            self.assertEqual(
                (row.source, row.version, row.component, row.sha),
                ("git", "1.0.0", "", "abc"),
            )

            row = store.ensure(
                "a1",
                "v1.0.0",
                "github",
                name="First",
                url="https://gh/r/1",
                author="ada",
            )
            self.assertEqual(
                (row.source, row.name, row.author, row.sha),
                ("github", "First", "ada", "abc"),
            )

            row = store.ensure("a1", "v1.0.0", "git", sha="def")
            self.assertEqual(
                (row.source, row.name, row.sha), ("github", "First", "abc")
            )

            row = store.ensure("a1", "v1.0.0", "platform", body="## notes")
            self.assertEqual(
                (row.source, row.body, row.name), ("platform", "## notes", "First")
            )

            self.assertEqual(len(s.query(type(row)).filter_by(app_id="a1").all()), 1)

    def test_any_source_name_is_accepted(self):
        with self.app.state.db.session() as s:
            row = self.store(s).ensure(
                "a1", "v2.0.0", "batatinha", name="from elsewhere"
            )

        self.assertEqual((row.source, row.name), ("batatinha", "from elsewhere"))

    def test_the_clones_tags_become_rows(self):
        tags = [
            {"tag": "v0.2.0", "sha": "bbb", "date": "2026-09-17"},
            {"tag": "web/v0.1.0", "sha": "aaa", "date": "2026-09-16"},
        ]

        with self.app.state.db.session() as s:
            self.store(s).from_tags("a1", tags)

        body = self.client.get(
            "/api/v1/projects/p1/apps/a1/imports", headers=self.h()
        ).json()
        self.assertEqual(
            sorted(
                (r["tag"], r["component"], r["version"], r["source"])
                for r in body["releases"]
            ),
            [("v0.2.0", "", "0.2.0", "git"), ("web/v0.1.0", "web", "0.1.0", "git")],
        )
        self.assertEqual(body["releases"][0]["published_at"][:10], "2026-09-17")

    def test_sync_imports_the_clones_tags(self):
        res = self.client.post("/api/v1/projects/p1/apps/a1/imports", headers=self.h())

        self.assertEqual(res.status_code, 200, res.text)
        tags = [r["tag"] for r in res.json()["releases"]]
        self.assertTrue(tags, "the fixture repository carries a tag")
        self.assertTrue(all(r["source"] == "git" for r in res.json()["releases"]))

    def test_a_deployment_references_its_release(self):
        from app.core.db.models import App
        from app.repositories.configuration.config_store import ConfigStore
        from app.services.deployments import DeploymentRecords

        ConfigStore(self.app.state.db).set(
            self.registry_id,
            {
                "deploy": {
                    "targets": [
                        {"name": "lambda", "kind": "aws/lambda"},
                        {
                            "name": "api-image",
                            "kind": "docker",
                            "run_by": "manual",
                            "image": "ghcr.io/a/b",
                            "component": "api",
                        },
                    ]
                }
            },
        )

        with self.app.state.db.session() as s:
            records = DeploymentRecords(s, self.app.state.sealer)
            app = s.get(App, "a1")
            config = ConfigStore(self.app.state.db).config_of(self.registry_id)
            rows = records.record_platform(
                app,
                config,
                [DeployResult(ok=True, target="lambda", version="1.5.0")],
                "prod",
                "job-9",
                "Ana",
                datetime(2026, 9, 17),
            )
            release = self.store(s).get("a1", "v1.5.0")
            self.assertIsNotNone(release)
            self.assertEqual(rows[0].release_id, release.id)

            manual = records.record_manual(
                app, config, "api-image", "0.22.0", None, None, "sha1", True, "Ana"
            )
            self.assertEqual(
                self.store(s).get("a1", "api/v0.22.0").id, manual.release_id
            )

        body = self.client.get(
            "/api/v1/projects/p1/apps/a1/deployments", headers=self.h()
        ).json()
        self.assertTrue(all(d["release_id"] for d in body["deployments"]))
