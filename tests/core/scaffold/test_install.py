"""action_platform.core.scaffold.install — bringing an existing repository onto the platform."""

from __future__ import annotations

import subprocess

from action_platform.core.scaffold import install
from action_platform.core.scaffold.install import InstallError
from action_platform.settings import settings
from tests.support import TempCase, git, install_templates


class InstallCase(TempCase):
    def setUp(self):
        super().setUp()
        self.templates = install_templates(self.tmp_path / "templates")
        self.patch(settings, "TEMPLATES_DIR", str(self.templates))
        self.repo = self.tmp_path / "existing"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "master")
        git(self.repo, "remote", "add", "origin", "git@github.com:acme/existing.git")
        (self.repo / "pyproject.toml").write_text("[project]\nname = 'x'\n")
        (self.repo / ".github/workflows").mkdir(parents=True)
        (self.repo / ".github/workflows/code-quality.yml").write_text("name: theirs\n")


class InstallTest(InstallCase):
    def test_creates_missing_keeps_existing(self):
        plan = install.install(self.repo)

        self.assertEqual(plan.language, "python")
        self.assertIn("platform.toml", plan.created)
        self.assertIn(".code_quality/", plan.created)
        self.assertIn(".github/workflows/gitflow.yml", plan.created)
        self.assertIn(".github/workflows/code-quality.yml", plan.skipped)
        self.assertEqual(
            (self.repo / ".github/workflows/code-quality.yml").read_text(),
            "name: theirs\n",
        )
        manifest = (self.repo / "platform.toml").read_text()
        self.assertIn('repo = "acme/existing"', manifest)
        self.assertIn('ci = "github"', manifest)
        self.assertIn('name = "existing"', manifest)
        self.assertTrue(plan.hooks_installed)
        self.assertTrue((self.repo / ".git/hooks/pre-commit").exists())
        self.assertTrue((self.repo / ".git/hooks/gitflow.sh").exists())
        self.assertEqual(git(self.repo, "status", "--porcelain").count(".git/"), 0)

    def test_dry_run_writes_nothing(self):
        plan = install.install(self.repo, dry_run=True)

        self.assertIn("platform.toml", plan.created)
        self.assertFalse((self.repo / "platform.toml").exists())

    def test_gitlab_ci_flag_and_platform_toml_ci(self):
        self.assertIn(".gitlab-ci.yml", install.install(self.repo, ci="gitlab").created)

        (self.repo / "platform.toml").write_text(
            '[project]\nname = "x"\nci = "gitlab"\nlanguage = "python"\n'
        )
        plan = install.install(self.repo)
        self.assertEqual(plan.ci, "gitlab")

    def test_not_a_git_repository(self):
        with self.assertRaisesRegex(InstallError, "not a git repository"):
            install.install(self.tmp_path)

    def test_without_a_language_only_config_ci_and_hooks(self):
        bare = self.tmp_path / "nolang"
        bare.mkdir()
        git(bare, "init", "-q")

        plan = install.install(bare)

        self.assertEqual(plan.language, "")
        self.assertIn("platform.toml", plan.created)
        self.assertFalse((bare / ".code_quality").exists())
        self.assertFalse((bare / ".github/workflows/code-quality.yml").exists())
        self.assertTrue((bare / ".github/workflows/gitflow.yml").exists())
        self.assertIn('language = ""', (bare / "platform.toml").read_text())

    def test_last_version_starts_at_zero_or_at_the_newest_tag(self):
        fresh = self.tmp_path / "fresh"
        fresh.mkdir()
        (fresh / "pyproject.toml").write_text('[project]\nname = "fresh"\n')
        git(fresh, "init", "-q")
        install.install(fresh)
        self.assertEqual((fresh / "LAST_VERSION").read_text(), "0.0.0\n")

        tagged = self.tmp_path / "tagged"
        tagged.mkdir()
        (tagged / "pyproject.toml").write_text('[project]\nname = "tagged"\n')
        git(tagged, "init", "-q")
        git(tagged, "commit", "-q", "--allow-empty", "-m", "chore: first")
        git(tagged, "tag", "v2.3.4")
        install.install(tagged)
        self.assertEqual((tagged / "LAST_VERSION").read_text(), "2.3.4\n")


class HooksTest(InstallCase):
    def test_own_hooks_are_refreshed(self):
        install.install(self.repo)
        (self.repo / ".git/hooks/pre-commit").write_text(
            "# action-platform hook\nbroken"
        )

        install.install(self.repo)

        self.assertIn(
            "gitflow_branch", (self.repo / ".git/hooks/pre-commit").read_text()
        )

    def test_existing_hooks_are_kept_and_chained(self):
        hooks = self.repo / ".git/hooks"
        hooks.mkdir(exist_ok=True)
        (hooks / "pre-commit").write_text("#!/bin/sh\necho husky > .ran\n")
        (hooks / "pre-commit").chmod(0o755)

        plan = install.install(self.repo)

        self.assertEqual(plan.hooks_preserved, ["pre-commit"])
        self.assertIn("gitflow_branch", (hooks / "pre-commit").read_text())
        self.assertTrue(
            (hooks / "pre-commit.pre-action-platform")
            .read_text()
            .startswith("#!/bin/sh")
        )

        git(self.repo, "checkout", "-q", "-b", "feature/9")
        subprocess.run([str(hooks / "pre-commit")], cwd=self.repo, check=True)
        self.assertEqual((self.repo / ".ran").read_text().strip(), "husky")

        install.install(self.repo)
        self.assertTrue(
            (hooks / "pre-commit.pre-action-platform")
            .read_text()
            .startswith("#!/bin/sh")
        )

    def test_versioned_hooks_path_is_left_alone(self):
        (self.repo / ".husky").mkdir()
        (self.repo / ".husky" / "pre-commit").write_text("#!/bin/sh\n")
        git(self.repo, "add", ".husky")
        git(self.repo, "commit", "-q", "-m", "chore: husky")
        git(self.repo, "config", "core.hooksPath", ".husky")

        plan = install.install(self.repo)

        self.assertFalse(plan.hooks_installed)
        self.assertIn("versioned", plan.hooks_skipped or "")
        self.assertEqual(
            (self.repo / ".husky" / "pre-commit").read_text(), "#!/bin/sh\n"
        )
        self.assertFalse((self.repo / ".git/hooks/gitflow.sh").exists())


class CiFollowsTheRemoteTest(TempCase):
    def test_a_gitlab_remote_gets_gitlab_ci(self):
        from action_platform.settings import settings
        from tests.support import git, template_repo

        self.patch(
            settings, "TEMPLATES_DIR", str(template_repo(self.tmp_path / "official"))
        )
        repo = self.tmp_path / "svc"
        repo.mkdir()
        (repo / "pyproject.toml").write_text('[project]\nname = "svc"\n')
        git(repo, "init", "-q", "-b", "main")
        git(repo, "remote", "add", "origin", "https://gitlab.com/acme/svc.git")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "chore: init")

        plan = install.install(repo)

        self.assertEqual(plan.ci, "gitlab")
        self.assertIn(".gitlab-ci.yml", plan.created)
        self.assertFalse(any(".github" in f for f in plan.created))
