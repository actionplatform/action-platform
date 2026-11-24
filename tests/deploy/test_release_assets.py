"""deploy/release-assets.sh — the compose files of an api tag with every image pinned."""

import base64
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "deploy" / "release-assets.sh"

COMPOSE = "services:\n  api:\n    image: ${AP_IMAGE_API:?set it}\n"
ENV_EXAMPLE = (
    "PUBLIC_URL=http://127.0.0.1:3000\nAP_IMAGE_API=\nAP_IMAGE_WORKER=\nAP_IMAGE_WEB=\n"
)
TOML = '[config]\n\n[config.env]\nPUBLIC_URL = "https://${main_domain}"\n'


class ReleaseAssetsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "repo"
        self.out = Path(self.tmp.name) / "dist"
        (self.repo / "deploy" / "dokploy").mkdir(parents=True)
        (self.repo / "deploy" / "docker-compose.yml").write_text(COMPOSE)
        (self.repo / "deploy" / "dokploy" / "docker-compose.yml").write_text(COMPOSE)
        (self.repo / "deploy" / ".env.example").write_text(ENV_EXAMPLE)
        (self.repo / "deploy" / "dokploy" / "template.toml").write_text(TOML)
        self.git("init", "-q")
        self.git("add", ".")
        self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
        self.git("tag", "api/v1.2.3")
        (self.repo / "deploy" / "docker-compose.yml").write_text(
            "changed after the tag\n"
        )

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True)

    def run_script(self, *args, prefix=None):
        env = {**os.environ}
        env.pop("AP_IMAGE_PREFIX", None)
        if prefix:
            env["AP_IMAGE_PREFIX"] = prefix
        return subprocess.run(
            ["sh", str(SCRIPT), *args],
            cwd=self.repo,
            capture_output=True,
            text=True,
            env=env,
        )

    def test_takes_the_files_from_the_api_tag_and_pins_every_image(self):
        result = self.run_script("1.2.3", "0.9.0", str(self.out))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.out / "docker-compose.yml").read_text(), COMPOSE)
        self.assertEqual((self.out / "docker-compose.dokploy.yml").read_text(), COMPOSE)
        self.assertEqual(
            (self.out / "env.example").read_text(),
            "PUBLIC_URL=http://127.0.0.1:3000\n"
            "AP_IMAGE_API=actionplatformio/action-platform-api:1.2.3\n"
            "AP_IMAGE_WORKER=actionplatformio/action-platform-worker:1.2.3\n"
            "AP_IMAGE_WEB=actionplatformio/action-platform-web:0.9.0\n",
        )
        template = json.loads(
            base64.b64decode((self.out / "dokploy-template.b64").read_text())
        )
        self.assertEqual(template["compose"], COMPOSE)
        self.assertTrue(
            template["config"].endswith(
                'AP_IMAGE_API = "actionplatformio/action-platform-api:1.2.3"\n'
                'AP_IMAGE_WORKER = "actionplatformio/action-platform-worker:1.2.3"\n'
                'AP_IMAGE_WEB = "actionplatformio/action-platform-web:0.9.0"\n'
            ),
            template["config"],
        )
        self.assertEqual(
            sorted(p.name for p in self.out.iterdir()),
            [
                "docker-compose.dokploy.yml",
                "docker-compose.yml",
                "dokploy-template.b64",
                "env.example",
            ],
        )

    def test_replaces_pinned_lines_and_honours_the_registry_prefix(self):
        (self.repo / "deploy" / "dokploy" / "template.toml").write_text(
            TOML
            + 'AP_IMAGE_API = "old"\nAP_IMAGE_WORKER = "old"\nAP_IMAGE_WEB = "old"\n'
        )
        self.git("add", ".")
        self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "pin")
        self.git("tag", "api/v1.3.0")

        result = self.run_script("1.3.0", "0.9.1", str(self.out), prefix="example/ap")

        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads(
            base64.b64decode((self.out / "dokploy-template.b64").read_text())
        )["config"]
        self.assertNotIn('"old"', config)
        self.assertEqual(config.count("AP_IMAGE_"), 3)
        self.assertIn('AP_IMAGE_WEB = "example/ap-web:0.9.1"', config)

    def test_fails_when_the_api_tag_does_not_exist(self):
        result = self.run_script("9.9.9", "0.9.0", str(self.out))

        self.assertNotEqual(result.returncode, 0)
