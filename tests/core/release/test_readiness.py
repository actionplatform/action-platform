from pathlib import Path

from action_platform.abc import DeployTarget
from action_platform.core.config import Config
from action_platform.core.context import Check, Context, DeployResult
from action_platform.core.exception import DeployError
from action_platform.core.release.deploy import Deployer
from action_platform.core.release.readiness import Readiness
from action_platform.testing.fixtures import TempCase, git, platform_repo


class Speaking(DeployTarget):
    name = "fake"

    def __init__(self, checks=None, error: str | None = None) -> None:
        self.checks = checks or []
        self.error = error
        self.stages: list[tuple[str, str]] = []

    def preflight(self, ctx: Context) -> None:
        pass

    def deploy(self, ctx: Context) -> DeployResult:
        return DeployResult(ok=True, target=self.name, version=ctx.next_version)

    def readiness(self, ctx: Context) -> list[Check]:
        self.stages.append((ctx.stage, ctx.next_version))

        if self.error:
            raise DeployError(self.error)

        return list(self.checks)


class ReadinessTest(TempCase):
    def setUp(self):
        super().setUp()
        self.repo = platform_repo(Path(self.tmp_path))

    def readiness(self, target: DeployTarget) -> Readiness:
        config = Config()
        config._deploy = [target]
        deployer = Deployer(config, self.repo)

        return Readiness(config, self.repo, deployer)

    def by_id(self, checks: list[Check]) -> dict[str, Check]:
        return {c.id: c for c in checks}

    def test_static_checks_pass_on_a_clean_release(self):
        target = Speaking([Check("aws.credentials", True, "account 1")])

        checks = self.by_id(self.readiness(target).check("prod", version="1.2.3"))

        self.assertTrue(checks["deploy.stage"].ok)
        self.assertTrue(checks["release.tag"].ok)
        self.assertTrue(checks["deploy.targets"].ok)
        self.assertEqual(checks["aws.credentials"].target, "fake")
        self.assertEqual(target.stages, [("prod", "1.2.3")])
        self.assertEqual(
            git(self.repo, "rev-parse", "--abbrev-ref", "HEAD"), "feature/1"
        )

    def test_a_manifest_off_the_tag_blocks(self):
        (self.repo / "pyproject.toml").write_text('[project]\nversion = "1.2.2"\n')
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "chore: manifest")
        git(self.repo, "tag", "v1.3.0")

        checks = self.by_id(self.readiness(Speaking()).check("dev", version="1.3.0"))

        self.assertFalse(checks["manifest.pyproject.toml"].ok)
        self.assertIn("1.2.2", checks["manifest.pyproject.toml"].detail)
        self.assertTrue(checks["manifest.pyproject.toml"].blocking)

    def test_a_missing_lockfile_warns_without_blocking(self):
        (self.repo / "package.json").write_text('{\n  "version": "1.3.0"\n}\n')
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "chore: manifest")
        git(self.repo, "tag", "v1.3.0")

        checks = self.by_id(self.readiness(Speaking()).check("dev", version="1.3.0"))

        self.assertFalse(checks["lockfile.package.json"].ok)
        self.assertFalse(checks["lockfile.package.json"].blocking)
        self.assertTrue(checks["manifest.package.json"].ok)

    def test_an_unknown_release_stops_at_the_tag(self):
        checks = self.readiness(Speaking()).check("prod", version="9.9.9")

        self.assertEqual([c.id for c in checks], ["deploy.stage", "release.tag"])
        self.assertFalse(checks[1].ok)
        self.assertIn("v1.2.3", checks[1].detail)

    def test_a_target_that_raises_becomes_a_failed_check(self):
        checks = self.by_id(
            self.readiness(Speaking(error="no credentials")).check(
                "prod", version="1.2.3"
            )
        )

        self.assertFalse(checks["target.readiness"].ok)
        self.assertEqual(checks["target.readiness"].detail, "no credentials")
        self.assertEqual(checks["target.readiness"].target, "fake")

    def test_an_unknown_stage_is_refused(self):
        checks = self.by_id(self.readiness(Speaking()).check("qa", version="1.2.3"))

        self.assertFalse(checks["deploy.stage"].ok)
