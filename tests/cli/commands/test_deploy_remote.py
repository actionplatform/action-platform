"""action_platform.cli.commands.deploy — the commands that read the hosted platform print its typed answers."""

from __future__ import annotations

from rich.console import Console

from action_platform.cli.commands import deploy
from action_platform.core.exception import ActionPlatformError
from action_platform.remote import client
from tests.support import TempCase

PROJECTS = [
    {
        "id": "p1",
        "name": "Shop",
        "slug": "shop",
        "apps": [{"id": "d1", "name": "orders", "registry_id": "r1"}],
    }
]
DEPLOYMENTS = {
    "targets": [
        {"name": "web", "kind": "docker", "run_by": "platform", "workflow": "ci.yml"}
    ],
    "deployments": [
        {
            "id": "x1",
            "target": "web",
            "kind": "docker",
            "stage": "prod",
            "version": "1.2.0",
            "status": "verified",
            "executor": "platform",
            "finished_at": "2026-09-01",
        }
    ],
    "error": "jenkins unreachable",
}
LOGS = {
    "lines": [{"seq": 1, "at": "2026-09-01T00:00:00", "line": "built"}],
    "next": 2,
    "status": "done",
    "finished": True,
}


class DeployRemoteTest(TempCase):
    def setUp(self):
        super().setUp()
        self.calls: list[tuple[str, str, object]] = []
        self.console = Console(record=True, width=200)
        self.patch(deploy, "console", self.console)
        self.patch(
            client.Remote,
            "from_credentials",
            classmethod(lambda cls, server=None: cls("https://p.example", "tok")),
        )

        def fake_request(method, url, body=None, token=None, **kwargs):
            self.calls.append((method, url, body))
            path = url.split("?")[0]

            if path.endswith("/projects"):
                return PROJECTS

            if path.endswith("/logs"):
                return LOGS

            if method == "POST" and path.endswith("/deployments"):
                return {**DEPLOYMENTS["deployments"][0], "version": body["version"]}

            return DEPLOYMENTS

        self.patch(client, "_request", fake_request)

    def test_deployments_prints_targets_and_what_arrived(self):
        deploy.deployments(app="orders", sync=False)

        out = self.console.export_text()
        self.assertIn("web docker · platform · ci.yml", out)
        self.assertIn("1.2.0 prod  verified  platform  2026-09-01", out)
        self.assertIn("jenkins unreachable", out)
        self.assertTrue(self.calls[-1][1].endswith("/projects/p1/apps/d1/deployments"))

    def test_record_sends_the_app_of_its_project(self):
        deploy.record(
            target="web", version="1.3.0", stage=None, url=None, failed=False, app="r1"
        )

        method, url, body = self.calls[-1]
        self.assertEqual(method, "POST")
        self.assertTrue(url.endswith("/projects/p1/apps/d1/deployments"))
        self.assertIn("recorded web 1.3.0 verified", self.console.export_text())

    def test_logs_prints_each_line_and_the_status(self):
        deploy.logs(job="j1", follow=False)

        out = self.console.export_text()
        self.assertIn("built", out)
        self.assertIn("job done", out)

    def test_unknown_app_is_a_readable_error(self):
        with self.assertRaisesRegex(ActionPlatformError, "no app 'nope'"):
            deploy.deployments(app="nope", sync=False)
