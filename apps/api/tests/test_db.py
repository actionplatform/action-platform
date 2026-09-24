"""Database the API owns: migrations from empty, adoption of a web-created schema, sessions, boot wiring."""

from __future__ import annotations

import unittest
from unittest import mock
from datetime import datetime, timedelta, timezone

from sqlalchemy import inspect, select

from action_platform.testing.fixtures import TempCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None

WEB_TABLES = {
    "user",
    "session",
    "account",
    "verification",
    "device_code",
    "organization",
    "member",
    "invitation",
    "team",
    "team_member",
    "project",
    "app",
    "source_host",
    "release",
    "pull_request",
    "template_source",
    "organization_setting",
    "api_token",
    "api_token_client",
}


class DatabaseTest(TempCase):
    def url(self, name: str = "ap.db") -> str:
        return f"sqlite:///{self.tmp_path / name}"

    def test_migrate_creates_every_table_and_reaches_head(self):
        from app.core.db import Database

        db = Database(self.url())
        self.assertEqual(db.migrate(), db.head_revision())
        self.assertTrue(
            WEB_TABLES
            | {
                "job",
                "ci_host",
                "ci_run",
                "deployment",
                "release_readiness",
                "job_log",
                "scope",
            }
            <= set(inspect(db.engine).get_table_names())
        )
        self.assertEqual(db.migrate(), "0021")

    def test_web_created_schema_is_adopted_not_recreated(self):
        from app.core.db import Base, Database
        from app.core.db.models import (
            AppConfig,
            CiHost,
            CiRun,
            Deployment,
            Draft,
            Job,
            OAuthApp,
            PluginOption,
            RegistryEntry,
            SigningKey,
        )

        db = Database(self.url())
        ours = {
            Job.__tablename__,
            RegistryEntry.__tablename__,
            OAuthApp.__tablename__,
            Draft.__tablename__,
            PluginOption.__tablename__,
            SigningKey.__tablename__,
            AppConfig.__tablename__,
            CiHost.__tablename__,
            CiRun.__tablename__,
            Deployment.__tablename__,
        }
        Base.metadata.create_all(
            db.engine,
            tables=[t for t in Base.metadata.sorted_tables if t.name not in ours],
        )
        self.assertTrue(db.adopted_from_web())
        self.assertEqual(db.migrate(), "0021")
        self.assertIn("job", inspect(db.engine).get_table_names())
        self.assertFalse(db.adopted_from_web())

    def test_session_commits_and_cascades(self):
        from app.core.db import Database
        from app.core.db.models import App, Organization, Project

        db = Database(self.url())
        db.migrate()

        with db.session() as s:
            s.add(Organization(id="o1", name="Acme", slug="acme"))
            s.add(Project(id="p1", organization_id="o1", name="Web", slug="web"))
            s.add(App(id="a1", project_id="p1", registry_id="r1", name="site"))

        with db.session() as s:
            self.assertEqual(
                s.scalar(select(App.name).where(App.registry_id == "r1")), "site"
            )
            s.delete(s.get(Organization, "o1"))

        with db.session() as s:
            self.assertIsNone(s.get(App, "a1"))

    def test_session_rolls_back_on_error(self):
        from app.core.db import Database
        from app.core.db.models import Organization

        db = Database(self.url())
        db.migrate()

        with self.assertRaises(RuntimeError):
            with db.session() as s:
                s.add(Organization(id="o1", name="Acme", slug="acme"))
                raise RuntimeError("boom")

        with db.session() as s:
            self.assertIsNone(s.get(Organization, "o1"))

    def test_job_dedupe_and_defaults(self):
        from app.core.db import Database
        from app.core.db.models import Job
        from sqlalchemy.exc import IntegrityError

        db = Database(self.url())
        db.migrate()

        with db.session() as s:
            s.add(Job(id="j1", kind="sync", app_id="a1", dedupe_key="a1"))

        with db.session() as s:
            job = s.get(Job, "j1")
            self.assertEqual(
                (job.status, job.attempts, job.payload), ("queued", 0, "{}")
            )
            self.assertLess(
                datetime.now(timezone.utc).replace(tzinfo=None) - job.run_after,
                timedelta(minutes=1),
            )

        with self.assertRaises(IntegrityError):
            with db.session() as s:
                s.add(Job(id="j2", kind="sync", app_id="a1", dedupe_key="a1"))

    def test_url_normalization(self):
        from app.core.db import normalize_url

        self.assertEqual(
            normalize_url("postgres://u:p@h/db"), "postgresql+psycopg://u:p@h/db"
        )
        self.assertEqual(
            normalize_url("postgresql://u:p@h/db"), "postgresql+psycopg://u:p@h/db"
        )
        self.assertEqual(normalize_url("mysql://u:p@h/db"), "mysql+pymysql://u:p@h/db")
        self.assertEqual(normalize_url("sqlite:///x.db"), "sqlite:///x.db")

    def test_empty_url_is_a_config_error(self):
        from app.core.db import Database

        from action_platform.core.exception import ConfigError

        with self.assertRaises(ConfigError):
            Database("")

    def test_without_auto_migrate_the_app_reports_readiness(self):
        from fastapi.testclient import TestClient

        from app.api.app import build
        from app.core.db import Database

        with mock.patch.dict("os.environ", {"AP_DATABASE_AUTO_MIGRATE": "0"}):
            behind = build(database_url=self.url(), auth_secret="s" * 32, token="t")
            before = TestClient(behind).get("/api/version").json()
            Database(self.url()).migrate()
            after = TestClient(behind).get("/api/version").json()

        self.assertEqual((before["ready"], before["database"]), (False, "behind"))
        self.assertEqual((after["ready"], after["database"]), (True, "up to date"))


@unittest.skipUnless(TestClient, "fastapi is not installed")
class BootTest(TempCase):
    def setUp(self):
        super().setUp()
        self.setenv("AP_HOME", str(self.tmp_path / "home"))
        self.setenv("AP_ALLOW_UNAUTHENTICATED", "1")

    def test_build_migrates_when_url_given(self):
        from app.api.app import build

        app = build(database_url=f"sqlite:///{self.tmp_path / 'boot.db'}")
        self.assertEqual(app.state.db.current_revision(), app.state.db.head_revision())

    def test_build_without_url_refuses(self):
        from app.api.app import build

        from action_platform.core.exception import ConfigError

        with self.assertRaisesRegex(ConfigError, "AP_DATABASE_URL"):
            build(database_url="")
