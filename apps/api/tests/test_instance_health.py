"""Instance health: the worker heartbeat, the open probe, the owner's view, the test email and jobs nobody takes."""

from __future__ import annotations

from datetime import timedelta
from unittest import mock

from typer.testing import CliRunner

from action_platform.core.exception import ProviderError
from app.core.db.models import Worker
from app.core.shared.clock import now
from tests.test_access import GateCase


class Outbox:
    def __init__(self) -> None:
        self.sent = []
        self.fail = None

    def send(self, mail) -> None:
        if self.fail:
            raise ProviderError(self.fail)

        self.sent.append(mail)


class HealthCase(GateCase):
    def beat(self, name="w", kinds=("sync", "release"), ago=0):
        from app.services.jobs.workers import Workers

        Workers(self.app.state.db).beat(name, list(kinds), "host-1")

        if ago:
            with self.app.state.db.session() as s:
                s.get(Worker, name).last_seen = now() - timedelta(seconds=ago)

    def both(self):
        self.beat("light", ("sync", "release"))
        self.beat("deploy", ("deploy", "destroy"))

    def health(self):
        return self.client.get("/api/health")

    def detail(self, token=None):
        return self.client.get("/api/v1/instance/health", headers=self.h(token))

    def developer(self) -> str:
        invitation = self.client.post(
            "/api/v1/invitations",
            json={"email": "dev@example.com", "role": "developer"},
            headers=self.h(),
        ).json()
        signed = self.client.post(
            "/api/auth/sign-up",
            json={
                "name": "Dev",
                "email": "dev@example.com",
                "password": "password1",
                "invitation_id": invitation["id"],
            },
        )

        return signed.json()["session"]["token"]


class ProbeTest(HealthCase):
    def test_open_without_any_token(self):
        res = self.health()

        self.assertEqual(res.status_code, 503)
        self.assertEqual(
            res.json(),
            {
                "status": "unavailable",
                "database": True,
                "migrations": True,
                "workers": {"light": False, "deploy": False},
            },
        )

    def test_ok_once_each_group_has_a_live_worker(self):
        self.beat("light", ("sync", "release"))
        self.assertEqual(
            self.health().json()["workers"], {"light": True, "deploy": False}
        )
        self.assertEqual(self.health().status_code, 503)

        self.beat("deploy", ("deploy", "destroy"))
        res = self.health()

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")

    def test_a_worker_silent_for_a_minute_no_longer_counts(self):
        self.both()
        self.beat("deploy", ("deploy",), ago=61)

        res = self.health()

        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.json()["workers"], {"light": True, "deploy": False})

    def test_pending_migrations_are_reported(self):
        self.both()

        with mock.patch("app.core.db.database.Database.behind", return_value=True):
            res = self.health()

        self.assertEqual(res.status_code, 503)
        self.assertFalse(res.json()["migrations"])
        self.assertEqual(res.json()["workers"], {"light": False, "deploy": False})

    def test_an_unreachable_database_is_reported(self):
        with mock.patch.object(
            self.app.state.db.engine, "connect", side_effect=OSError("refused")
        ):
            res = self.health()

        self.assertEqual(res.status_code, 503)
        self.assertFalse(res.json()["database"])


class OwnerViewTest(HealthCase):
    def test_only_an_owner_reads_it(self):
        self.assertEqual(self.detail().status_code, 200)
        self.assertEqual(self.detail(self.developer()).status_code, 403)
        self.assertEqual(self.client.get("/api/v1/instance/health").status_code, 401)

    def test_queue_depth_age_and_workers(self):
        from app.services.jobs import JobQueue

        self.both()
        queue = JobQueue(self.app.state.db)
        org = self.org["id"]
        queue.enqueue("sync", {}, organization_id=org)
        queue.enqueue("sync", {}, organization_id=org, dedupe_key="b", app_id="a")
        queue.enqueue("deploy", {}, organization_id=org)
        queue.claim("w", ["deploy"])
        with self.app.state.db.session() as s:
            from app.core.db.models import Job

            s.query(Job).filter(Job.kind == "sync").update(
                {"run_after": now() - timedelta(seconds=300)}
            )

        body = self.detail().json()
        queue_rows = {row["kind"]: row for row in body["queue"]}

        self.assertEqual(body["status"], "ok")
        self.assertEqual(queue_rows["sync"]["queued"], 2)
        self.assertGreaterEqual(queue_rows["sync"]["oldest_queued_seconds"], 300)
        self.assertEqual(queue_rows["sync"]["group"], "light")
        self.assertTrue(queue_rows["sync"]["worker_running"])
        self.assertEqual(queue_rows["deploy"]["running"], 1)
        self.assertEqual(queue_rows["deploy"]["group"], "deploy")
        self.assertEqual(
            {w["name"]: (w["alive"], w["kinds"]) for w in body["workers_seen"]},
            {
                "light": (True, ["sync", "release"]),
                "deploy": (True, ["deploy", "destroy"]),
            },
        )
        self.assertNotIn("host", body["workers_seen"][0])
        self.assertIn("version", body)
        self.assertIn("api", body)

    def test_an_owner_does_not_see_another_organizations_queue(self):
        from app.services.jobs import JobQueue

        JobQueue(self.app.state.db).enqueue("sync", {}, organization_id=self.org["id"])
        other = self.client.post(
            "/api/auth/organizations",
            json={"name": "Beta", "slug": "beta"},
            headers=self.h(),
        ).json()

        mine = self.client.get(
            "/api/v1/instance/health",
            headers={**self.h(), "X-Organization": self.org["id"]},
        ).json()
        theirs = self.client.get(
            "/api/v1/instance/health",
            headers={**self.h(), "X-Organization": other["id"]},
        ).json()

        self.assertEqual([r["kind"] for r in mine["queue"]], ["sync"])
        self.assertEqual(theirs["queue"], [])

    def test_integrations_say_what_is_configured(self):
        body = self.detail().json()["integrations"]

        self.assertEqual(body["smtp"]["configured"], False)
        self.assertEqual(
            body["google"],
            {
                "configured": False,
                "redirect_uri": "https://ap.example.com/api/sign-in/google/callback",
            },
        )
        self.assertFalse(body["sentry_api"])
        self.assertIn("github", {a["provider"] for a in body["oauth_apps"]})


class TestEmailTest(HealthCase):
    def send(self, token=None):
        return self.client.post("/api/v1/instance/test-email", headers=self.h(token))

    def test_sends_to_the_signed_in_owner(self):
        outbox = Outbox()
        self.app.state.mailer = outbox

        res = self.send()

        self.assertEqual(
            res.json(), {"sent": True, "to": "ana@example.com", "error": None}
        )
        self.assertEqual([m.to for m in outbox.sent], ["ana@example.com"])

    def test_returns_the_smtp_error_text(self):
        outbox = Outbox()
        outbox.fail = "cannot send email through smtp.example.com: 535 bad credentials"
        self.app.state.mailer = outbox

        res = self.send()

        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["sent"])
        self.assertIn("535 bad credentials", res.json()["error"])

    def test_without_smtp_it_says_so(self):
        res = self.send()

        self.assertFalse(res.json()["sent"])
        self.assertIn("AP_SMTP_HOST", res.json()["error"])

    def test_not_for_a_member(self):
        self.assertEqual(self.send(self.developer()).status_code, 403)


class StalledJobTest(HealthCase):
    def queued(self, kind="sync", age=300):
        from app.core.db.models import Job
        from app.services.jobs import JobQueue

        job = JobQueue(self.app.state.db).enqueue(
            kind, {}, organization_id=self.org["id"]
        )
        with self.app.state.db.session() as s:
            s.get(Job, job.id).run_after = now() - timedelta(seconds=age)

        return job.id

    def job(self, id):
        return self.client.get(f"/api/v1/jobs/{id}", headers=self.h()).json()

    def test_flagged_when_no_live_worker_takes_the_kind(self):
        id = self.queued()

        self.assertTrue(self.job(id)["no_worker"])
        self.beat("light", ("sync",))
        self.assertFalse(self.job(id)["no_worker"])

    def test_a_worker_for_another_kind_does_not_help(self):
        id = self.queued("deploy")
        self.beat("light", ("sync",))

        self.assertTrue(self.job(id)["no_worker"])

    def test_a_fresh_job_is_not_flagged_yet(self):
        self.assertFalse(self.job(self.queued(age=30))["no_worker"])

    def test_a_running_job_is_not_flagged(self):
        from app.services.jobs import JobQueue

        id = self.queued()
        JobQueue(self.app.state.db).claim("w")

        self.assertFalse(self.job(id)["no_worker"])

    def test_the_log_poll_carries_it(self):
        id = self.queued("deploy")
        res = self.client.get(f"/api/v1/jobs/{id}/logs", headers=self.h()).json()

        self.assertEqual((res["kind"], res["no_worker"]), ("deploy", True))


class HeartbeatTest(HealthCase):
    def test_a_worker_writes_its_kinds_and_host(self):
        from app.services.jobs.worker import Worker as Runner

        Runner(self.app.state.db, self.app.state.secrets, "main").run(
            once=True, kinds=["sync", "release"]
        )

        with self.app.state.db.session() as s:
            row = s.get(Worker, "main")

        self.assertEqual(row.kinds, "sync,release")
        self.assertTrue(row.host)
        self.assertLess(now() - row.last_seen, timedelta(seconds=30))

    def test_every_kind_when_none_is_named(self):
        from app.services.jobs.worker import Worker as Runner

        Runner(self.app.state.db, self.app.state.secrets, "all").run(once=True)

        with self.app.state.db.session() as s:
            kinds = s.get(Worker, "all").kinds.split(",")

        self.assertIn("sync", kinds)
        self.assertIn("deploy", kinds)

    def test_old_rows_are_forgotten(self):
        self.beat("gone", ("sync",), ago=3 * 86400)
        from app.services.jobs.worker import Worker as Runner

        Runner(self.app.state.db, self.app.state.secrets, "main").run(once=True)

        with self.app.state.db.session() as s:
            self.assertIsNone(s.get(Worker, "gone"))


class CheckCommandTest(HealthCase):
    def check(self, *args):
        from app.cli.app import app

        self.setenv("AP_DATABASE_URL", f"sqlite:///{self.tmp_path / 'gate.db'}")

        return CliRunner().invoke(app, ["worker", "--check", *args])

    def test_alive_worker_passes(self):
        self.beat("deploy", ("deploy",))
        res = self.check("--name", "deploy")

        self.assertEqual(res.exit_code, 0, res.output)

    def test_silent_or_unknown_worker_fails(self):
        self.beat("deploy", ("deploy",), ago=120)

        self.assertEqual(self.check("--name", "deploy").exit_code, 1)
        self.assertEqual(self.check("--name", "other").exit_code, 1)

    def test_it_needs_a_name(self):
        self.assertEqual(self.check().exit_code, 2)
