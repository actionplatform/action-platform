"""deploy/install.sh — resolves pinned api/web versions and writes them to .env."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "deploy" / "install.sh"

RELEASES = [
    {"tag_name": "web/v0.34.0-rc.1", "prerelease": True},
    {"tag_name": "v0.40.0"},
    {"tag_name": "api/v0.42.0-rc.2", "prerelease": True},
    {"tag_name": "web/v0.33.0"},
    {"tag_name": "api/v0.41.2"},
    {"tag_name": "api/v0.9.10"},
    {"tag_name": "api/v0.41.10"},
    {"tag_name": "web/v0.4.0"},
    {"tag_name": "api/v0.39.4"},
]


def run(snippet, stdin="", cwd=None, env=None):
    return subprocess.run(
        ["sh", "-c", f'. "{SCRIPT}"; {snippet}'],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=cwd,
        env={**os.environ, "AP_INSTALL_SOURCE_ONLY": "1", **(env or {})},
    )


class LatestStableTest(unittest.TestCase):
    def test_picks_the_newest_stable_tag_of_each_family(self):
        for payload in (json.dumps(RELEASES, indent=2), json.dumps(RELEASES)):
            api = run("latest_stable api", payload)
            web = run("latest_stable web", payload)

            self.assertEqual(api.stdout.strip(), "0.41.10")
            self.assertEqual(web.stdout.strip(), "0.33.0")

    def test_nothing_when_the_family_has_no_stable_release(self):
        payload = json.dumps([{"tag_name": "web/v1.0.0-rc.1"}, {"tag_name": "v1.0.0"}])

        self.assertEqual(run("latest_stable web", payload).stdout, "")


class ResolveVersionsTest(unittest.TestCase):
    def test_pins_both_components_without_listing_releases(self):
        result = run(
            'resolve_versions; echo "$API_VERSION $WEB_VERSION"',
            env={"AP_REF": "api/v0.39.4", "AP_WEB_REF": "web/v0.32.3"},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "0.39.4 0.32.3")

    def test_refuses_a_ref_that_is_not_a_component_tag(self):
        for ref in ("v0.32.1", "master", "api/v0.42.0-rc.1", "web/v0.33.0"):
            result = run(
                "resolve_versions", env={"AP_REF": ref, "AP_WEB_REF": "web/v0.33.0"}
            )

            self.assertNotEqual(result.returncode, 0, ref)
            self.assertIn("AP_REF must be a release tag (api/vX.Y.Z)", result.stderr)


class EnvFileTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.env = Path(self.dir.name) / ".env"

    def test_reads_the_running_version_from_the_image_tag(self):
        self.env.write_text(
            "AP_IMAGE_API=actionplatformio/action-platform-api:0.41.2\n"
            "AP_IMAGE_WEB=registry.local:5000/action-platform-web:0.33.0\n"
        )

        api = run("image_version AP_IMAGE_API", cwd=self.dir.name)
        web = run("image_version AP_IMAGE_WEB", cwd=self.dir.name)
        worker = run("image_version AP_IMAGE_WORKER", cwd=self.dir.name)

        self.assertEqual(api.stdout.strip(), "0.41.2")
        self.assertEqual(web.stdout.strip(), "0.33.0")
        self.assertEqual(worker.stdout.strip(), "")

    def test_set_env_replaces_or_appends(self):
        self.env.write_text("PUBLIC_URL=x\nAP_IMAGE_API=\n# AP_IMAGE_WEB=old\n")

        run(
            "set_env AP_IMAGE_API api:1; set_env AP_IMAGE_WEB web:2",
            cwd=self.dir.name,
        )

        self.assertEqual(
            self.env.read_text(),
            "PUBLIC_URL=x\nAP_IMAGE_API=api:1\n# AP_IMAGE_WEB=old\nAP_IMAGE_WEB=web:2\n",
        )


class SetupHintTest(unittest.TestCase):
    def test_prints_the_setup_token_while_nobody_signed_up(self):
        result = run(
            'DIR=/opt/ap; compose() { [ "$1" = exec ] && echo ABCD-EFGH-IJKL-MNOP; return 0; }; setup_hint'
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("      ABCD-EFGH-IJKL-MNOP\n", result.stdout)
        self.assertIn(
            "docker compose exec api action-platform-api setup token", result.stdout
        )

    def test_says_sign_in_when_setup_is_closed(self):
        result = run(
            'DIR=/opt/ap; compose() { [ "$1" = exec ] && return 1; return 0; }; setup_hint'
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Open it and sign in.", result.stdout)
        self.assertNotIn("first account asks", result.stdout)


class SyntaxTest(unittest.TestCase):
    def test_parses_as_posix_sh(self):
        result = subprocess.run(
            ["sh", "-n", str(SCRIPT)], capture_output=True, text=True
        )

        self.assertEqual(result.returncode, 0, result.stderr)


class ComposeTest(unittest.TestCase):
    def test_images_are_required_and_never_pulled_on_every_start(self):
        deploy = SCRIPT.parent
        for path in (
            deploy / "docker-compose.yml",
            deploy / "dokploy" / "docker-compose.yml",
        ):
            text = path.read_text()

            self.assertNotIn("pull_policy", text, path)
            self.assertNotIn("action-platform-api:latest", text, path)
            self.assertNotIn("action-platform-worker:latest", text, path)
            self.assertNotIn("action-platform-web:latest", text, path)
            self.assertIn("${AP_IMAGE_API:?", text, path)
            self.assertIn("${AP_IMAGE_WEB:?", text, path)
