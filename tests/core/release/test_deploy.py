"""A deploy ships a release: it names a version or takes the tag HEAD sits on, checks the tag out for the duration, and puts the branch back."""

from pathlib import Path

from action_platform.abc import DeployTarget
from action_platform.core.config import Config
from action_platform.core.context import Context, DeployResult, Diagnosis
from action_platform.core.exception import ConfigError, DeployError
from action_platform.core.release.deploy import Deployer
from action_platform.testing.fixtures import TempCase, git, platform_repo


class Recording(DeployTarget):
    name = "fake"

    def __init__(self) -> None:
        self.seen: list[tuple[str, str, str]] = []

    def preflight(self, ctx: Context) -> None:
        self.seen.append(
            (
                "preflight",
                ctx.next_version,
                git(ctx.repo_root, "rev-parse", "--abbrev-ref", "HEAD"),
            )
        )

    def deploy(self, ctx: Context) -> DeployResult:
        self.seen.append(
            (
                "deploy",
                ctx.next_version,
                (ctx.repo_root / "a.txt").exists() and "feature" or "tag",
            )
        )

        return DeployResult(ok=True, target=self.name, version=ctx.next_version)

    def rollback(self, ctx: Context, to_version: str | None = None) -> None:
        pass

    def diagnose(self, ctx: Context) -> Diagnosis:
        return Diagnosis(ok=True, target=self.name, status="ok")

    def delete(self, ctx: Context) -> None:
        pass


class DeployShipsAReleaseTest(TempCase):
    def setUp(self):
        super().setUp()
        self.repo = platform_repo(Path(self.tmp_path))
        self.target = Recording()
        config = Config.from_dict(
            {
                "scopes": [
                    {"name": "dev", "criticality": "test"},
                    {"name": "prod", "criticality": "high"},
                ]
            }
        )
        config._deploy = [self.target]
        self.deployer = Deployer(config, self.repo)

    def test_a_named_version_is_checked_out_and_the_branch_comes_back(self):
        results = self.deployer.deploy(version="1.2.3", stage="prod")

        self.assertEqual(results[0].version, "1.2.3")
        self.assertEqual(self.target.seen[0], ("preflight", "1.2.3", "HEAD"))
        self.assertEqual(self.target.seen[1][2], "tag")
        self.assertEqual(
            git(self.repo, "rev-parse", "--abbrev-ref", "HEAD"), "feature/1"
        )
        self.assertTrue((self.repo / "a.txt").exists())

    def test_head_off_a_tag_is_refused_without_a_version(self):
        with self.assertRaises(DeployError) as caught:
            self.deployer.deploy(stage="prod")

        self.assertIn("ships a release", str(caught.exception))
        self.assertEqual(self.target.seen, [])

    def test_head_on_a_tag_deploys_that_tag(self):
        git(self.repo, "checkout", "-q", "v1.2.3")

        results = self.deployer.deploy(dry_run=True, stage="prod")

        self.assertEqual(results[0].version, "1.2.3")

    def test_an_unknown_version_names_the_tags_that_exist(self):
        with self.assertRaises(DeployError) as caught:
            self.deployer.deploy(version="9.9.9", stage="prod")

        self.assertIn("v1.2.3", str(caught.exception))

    def test_no_scope_no_deploy(self):
        config = Config()
        config._deploy = [self.target]

        with self.assertRaises(ConfigError) as caught:
            Deployer(config, self.repo).deploy(version="1.2.3", stage="prod")

        self.assertIn("no scope named 'prod'", str(caught.exception))
        self.assertEqual(self.target.seen, [])
