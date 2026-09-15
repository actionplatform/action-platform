"""action_platform.core.manifest — platform.toml bookkeeping without touching the rest of the file."""

from __future__ import annotations

import tomllib
import unittest

from action_platform.core.manifest.manifest import dump_toml

from action_platform.core.exception import TemplateError
from action_platform.core.manifest import (
    check_owner,
    check_repo,
    read_platform,
    toml_str,
    write_deploy_target,
    write_service,
    write_source_host,
)
from tests.support import TempCase

BASE = '[project]\nname = "x"\ntype = "web"\nlanguage = "python"\n'


class DeployTargetTest(TempCase):
    def test_appends_deploy_section(self):
        path = self.tmp_path / "platform.toml"
        path.write_text(BASE)

        write_deploy_target(path, "aws/lambda")

        self.assertTrue(
            path.read_text().endswith('\n[deploy]\ntarget = "aws/lambda"\n')
        )
        self.assertEqual(read_platform(self.tmp_path)["language"], "python")

    def test_replaces_existing_target(self):
        path = self.tmp_path / "platform.toml"
        path.write_text(BASE + '\n[deploy]\ntarget = "docker"\n')

        write_deploy_target(path, "aws/lambda")

        self.assertEqual(path.read_text().count("[deploy]"), 1)
        self.assertIn('target = "aws/lambda"', path.read_text())
        self.assertNotIn('target = "docker"', path.read_text())


class ServicesTest(TempCase):
    def test_upserts_within_the_table(self):
        path = self.tmp_path / "platform.toml"
        path.write_text(BASE + '\n[deploy]\ntarget = "docker"\n')

        write_service(path, "postgres", "docker")
        write_service(path, "redis", "docker")
        write_service(path, "postgres", "aws-rds")

        text = path.read_text()
        self.assertEqual(text.count("[services]"), 1)
        self.assertIn('postgres = "aws-rds"', text)
        self.assertNotIn('postgres = "docker"', text)
        self.assertIn('redis = "docker"', text)
        self.assertIn('target = "docker"', text)


class SourceHostTest(TempCase):
    def test_replaces_and_adds(self):
        path = self.tmp_path / "platform.toml"
        path.write_text(
            BASE
            + '\n[source_host]\nkind = "github"\nrepo = "a/b"\n\n[release]\nstrategy = "semver"\n'
        )

        write_source_host(path, "gitlab", "grp/b", "https://gitlab.example.com")

        text = path.read_text()
        self.assertEqual(text.count("[source_host]"), 1)
        self.assertIn('kind = "gitlab"', text)
        self.assertIn('repo = "grp/b"', text)
        self.assertIn('base_url = "https://gitlab.example.com"', text)
        self.assertNotIn('kind = "github"', text)
        self.assertIn('[release]\nstrategy = "semver"', text)

        plain = self.tmp_path / "plain.toml"
        plain.write_text(BASE)
        write_source_host(plain, "bitbucket", "ws/x")
        self.assertTrue(
            plain.read_text().endswith(
                '\n[source_host]\nkind = "bitbucket"\nrepo = "ws/x"\n'
            )
        )


class EscapingTest(TempCase):
    def test_toml_str_round_trips(self):
        for value in [
            "plain",
            'has "quote"',
            "line\nbreak",
            "back\\slash",
            "tab\there",
            "ctrl\x01x",
            'x"\n[deploy]\ntarget = "aws/lambda',
        ]:
            self.assertEqual(tomllib.loads(f"v = {toml_str(value)}\n")["v"], value)

    def test_writers_cannot_inject_tables(self):
        evil = 'x"\n[deploy]\ntarget = "aws/lambda'
        path = self.tmp_path / "platform.toml"
        path.write_text('[project]\nname = "demo"\n')

        write_source_host(path, "github", "acme/orders")
        write_deploy_target(path, evil)

        data = tomllib.loads(path.read_text())
        self.assertEqual(data["deploy"]["target"], evil)
        self.assertEqual(data["source_host"]["repo"], "acme/orders")

    def test_owner_and_repo_are_validated(self):
        path = self.tmp_path / "p.toml"
        path.write_text(BASE)

        with self.assertRaises(TemplateError):
            write_source_host(path, "github", 'acme/or"ders')
        with self.assertRaises(TemplateError):
            check_owner("-x")
        with self.assertRaises(TemplateError):
            check_repo("just-a-name")


if __name__ == "__main__":
    unittest.main()


class DumpTomlTest(unittest.TestCase):
    def test_round_trips_the_tables_platform_toml_holds(self):
        data = {
            "project": {
                "name": "shop",
                "type": "web",
                "language": "python",
                "ci": "github",
            },
            "source_host": {"kind": "github", "repo": "acme/shop"},
            "release": {"strategy": "semver", "changelog": "conventional"},
            "deploy": {
                "target": "aws/lambda",
                "region": "us-east-1",
                "retries": 2,
                "quiet": True,
            },
            "services": {"cache": {"kind": "redis"}},
            "components": {"web": {"path": "apps/web"}, "api": {"path": "apps/api"}},
        }

        self.assertEqual(tomllib.loads(dump_toml(data)), data)

    def test_a_quote_in_a_value_stays_inside_the_string(self):
        text = dump_toml({"project": {"name": 'a "quoted" name'}})

        self.assertEqual(tomllib.loads(text)["project"]["name"], 'a "quoted" name')
