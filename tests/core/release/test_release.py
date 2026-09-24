"""action_platform.core.release.release — rc off main, stable on main, components, refusals before writing."""

from __future__ import annotations

import subprocess
from unittest import mock

from action_platform.core.config import Config
from action_platform.core.exception import ReleaseError
from action_platform.core.flow.repository import Repository
from action_platform.core.release import release as releasing
from tests.support import TempCase, git as run, repo_with_origin


class ReleaseCase(TempCase):
    def setUp(self):
        super().setUp()
        self.repo = repo_with_origin(
            self.tmp_path,
            files={
                "LAST_VERSION": "0.3.1\n",
                "platform.toml": '[project]\nname = "x"\n',
            },
            message="chore: bootstrap",
        )
        run(self.repo, "tag", "v0.3.1")
        run(self.repo, "commit", "-q", "--allow-empty", "-m", "feat: x")

    def release(self, level: str, prerelease=None):
        return releasing.release(Config(), level, self.repo, prerelease=prerelease)


class SingleProjectTest(ReleaseCase):
    def test_stable_on_main(self):
        ctx = self.release("patch")

        self.assertEqual(ctx.next_version, "0.3.2")
        self.assertIn("v0.3.2", Repository(self.repo).tags())

    def test_rc_off_main_and_increments(self):
        run(self.repo, "checkout", "-qb", "feature/1")

        self.assertEqual(self.release("patch").next_version, "0.3.2-rc.1")

        run(self.repo, "commit", "-q", "--allow-empty", "-m", "fix: y")
        self.assertEqual(self.release("patch").next_version, "0.3.2-rc.2")

    def test_existing_tag_refused_before_writing(self):
        run(self.repo, "tag", "v0.3.2")
        before = run(self.repo, "rev-parse", "HEAD")

        with self.assertRaisesRegex(ReleaseError, "already exists"):
            self.release("patch")

        self.assertEqual(run(self.repo, "rev-parse", "HEAD"), before)
        self.assertEqual((self.repo / "LAST_VERSION").read_text(), "0.3.1\n")
        self.assertFalse((self.repo / "CHANGELOG.md").exists())

    def test_same_version_refused(self):
        run(self.repo, "tag", "-d", "v0.3.1")
        run(self.repo, "tag", "v0.1.0")

        with self.assertRaisesRegex(ReleaseError, "already the current version"):
            self.release("0.3.1")

    def test_a_repository_without_tags_starts_at_zero(self):
        run(self.repo, "tag", "-d", "v0.3.1")

        self.assertEqual(self.release("patch").next_version, "0.0.1")
        self.assertEqual((self.repo / "LAST_VERSION").read_text(), "0.0.1\n")


class ComponentTest(ReleaseCase):
    def setUp(self):
        super().setUp()
        (self.repo / "platform.toml").write_text(
            '[project]\nname = "x"\n\n[components.web]\npath = "apps/web"\n'
        )
        web = self.repo / "apps" / "web"
        web.mkdir(parents=True)
        (web / "LAST_VERSION").write_text("0.1.0\n")
        (web / "package.json").write_text(
            '{\n  "name": "web",\n  "version": "0.1.0"\n}\n'
        )
        run(self.repo, "add", "-A")
        run(self.repo, "commit", "-qm", "feat(web): scaffold")
        run(self.repo, "tag", "web/v0.1.0")
        (web / "page.tsx").write_text("x")
        run(self.repo, "add", "-A")
        run(self.repo, "commit", "-qm", "feat(web): page")
        (self.repo / "lib.py").write_text("x")
        run(self.repo, "add", "-A")
        run(self.repo, "commit", "-qm", "fix(core): lib")
        self.config = Config.from_toml(self.repo / "platform.toml")

    def test_component_has_own_version_tag_and_changelog(self):
        ctx = releasing.release(self.config, "minor", self.repo, component="web")

        self.assertEqual(ctx.next_version, "0.2.0")
        self.assertIn("web/v0.2.0", Repository(self.repo).tags())
        self.assertEqual(
            (self.repo / "apps/web/LAST_VERSION").read_text().strip(), "0.2.0"
        )
        self.assertEqual((self.repo / "LAST_VERSION").read_text().strip(), "0.3.1")
        self.assertIn(
            '"version": "0.2.0"', (self.repo / "apps/web/package.json").read_text()
        )
        self.assertIn("page", ctx.changelog)
        self.assertNotIn("lib", ctx.changelog)
        self.assertTrue((self.repo / "apps/web/CHANGELOG.md").exists())
        self.assertFalse((self.repo / "CHANGELOG.md").exists())
        self.assertEqual(
            run(self.repo, "log", "-1", "--format=%s"), "chore(release): web 0.2.0"
        )

    def test_root_release_excludes_component_commits(self):
        ctx = releasing.release(self.config, "patch", self.repo)

        self.assertEqual(ctx.next_version, "0.3.2")
        self.assertIn("v0.3.2", Repository(self.repo).tags())
        self.assertIn("lib", ctx.changelog)
        self.assertNotIn("page", ctx.changelog)
        self.assertEqual(
            (self.repo / "apps/web/LAST_VERSION").read_text().strip(), "0.1.0"
        )

    def test_component_rc_counts_only_its_own_tags(self):
        run(self.repo, "checkout", "-qb", "feature/2")
        run(self.repo, "tag", "v0.3.2-rc.1")

        ctx = releasing.release(self.config, "patch", self.repo, component="web")

        self.assertEqual(ctx.next_version, "0.1.1-rc.1")
        self.assertIn("web/v0.1.1-rc.1", Repository(self.repo).tags())

    def test_unknown_component(self):
        with self.assertRaisesRegex(ReleaseError, "unknown component: api"):
            releasing.release(self.config, "patch", self.repo, component="api")


class FailureTest(ReleaseCase):
    def setUp(self):
        super().setUp()
        self.releaser = releasing.Releaser(Config(), Repository(self.repo))
        self.before = run(self.repo, "rev-parse", "HEAD")

    def refused(self, step: str, stderr: str) -> subprocess.CalledProcessError:
        return subprocess.CalledProcessError(1, ["git", step], stderr=stderr)

    def test_a_failed_commit_undoes_the_writes_and_keeps_the_cause(self):
        cause = self.refused("commit", "hook said no")

        with mock.patch.object(self.releaser.repo, "commit", side_effect=cause):
            with self.assertRaisesRegex(ReleaseError, "hook said no") as caught:
                self.releaser.release("patch")

        self.assertIs(caught.exception.__cause__, cause)
        self.assertEqual((self.repo / "LAST_VERSION").read_text(), "0.3.1\n")
        self.assertFalse((self.repo / "CHANGELOG.md").exists())

    def test_a_failed_push_drops_the_tag_and_the_commit(self):
        cause = self.refused("push", "rejected")

        with mock.patch.object(self.releaser.repo, "push", side_effect=cause):
            with self.assertRaisesRegex(
                ReleaseError, "nothing was published"
            ) as caught:
                self.releaser.release("patch")

        self.assertIs(caught.exception.__cause__, cause)
        self.assertNotIn("v0.3.2", Repository(self.repo).tags())
        self.assertEqual(run(self.repo, "rev-parse", "HEAD"), self.before)

    def test_an_unexpected_error_is_not_disguised_as_a_release_error(self):
        with mock.patch.object(
            self.releaser.repo, "push", side_effect=RuntimeError("bug")
        ):
            with self.assertRaisesRegex(RuntimeError, "bug"):
                self.releaser.release("patch")
