"""action_platform.core.scaffold.installer — bringing an existing repository onto the platform."""

from __future__ import annotations

import subprocess
import unittest
from unittest import mock

from action_platform.core.flow.repository import Repository
from action_platform.core.scaffold import installer
from action_platform.core.scaffold.installer import InstallError
from tests.support import TempCase, git, install_templates


class InstallCase(TempCase):
    def setUp(self):
        super().setUp()
        self.templates = install_templates(self.tmp_path / "templates")
        self.setenv("ACTION_PLATFORM_TEMPLATES", str(self.templates))
        self.repo = self.tmp_path / "existing"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "master")
        git(self.repo, "remote", "add", "origin", "git@github.com:acme/existing.git")
        (self.repo / "pyproject.toml").write_text("[project]\nname = 'x'\n")
        (self.repo / ".github/workflows").mkdir(parents=True)
        (self.repo / ".github/workflows/code-quality.yml").write_text("name: theirs\n")


class InstallTest(InstallCase):
    def test_creates_missing_keeps_existing(self):
        plan = installer.install(self.repo)

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
        plan = installer.install(self.repo, dry_run=True)

        self.assertIn("platform.toml", plan.created)
        self.assertFalse((self.repo / "platform.toml").exists())

    def test_gitlab_ci_flag_and_platform_toml_ci(self):
        self.assertIn(
            ".gitlab-ci.yml", installer.install(self.repo, ci="gitlab").created
        )

        (self.repo / "platform.toml").write_text(
            '[project]\nname = "x"\nci = "gitlab"\nlanguage = "python"\n'
        )
        plan = installer.install(self.repo)
        self.assertEqual(plan.ci, "gitlab")

    def test_not_a_git_repository(self):
        with self.assertRaisesRegex(InstallError, "not a git repository"):
            installer.install(self.tmp_path)

    def test_without_a_language_only_config_ci_and_hooks(self):
        bare = self.tmp_path / "nolang"
        bare.mkdir()
        git(bare, "init", "-q")

        plan = installer.install(bare)

        self.assertEqual(plan.language, "")
        self.assertIn("platform.toml", plan.created)
        self.assertFalse((bare / ".code_quality").exists())
        self.assertFalse((bare / ".github/workflows/code-quality.yml").exists())
        self.assertTrue((bare / ".github/workflows/gitflow.yml").exists())
        self.assertIn('language = ""', (bare / "platform.toml").read_text())

    def test_ci_none_writes_no_pipeline(self):
        bare = self.tmp_path / "noci"
        bare.mkdir()
        git(bare, "init", "-q")

        plan = installer.install(bare, ci="none")

        self.assertEqual(plan.ci, "none")
        self.assertFalse((bare / ".github").exists())
        self.assertFalse((bare / ".gitlab-ci.yml").exists())
        self.assertIn('ci = "none"', (bare / "platform.toml").read_text())
        self.assertEqual(
            {f for f in plan.created if "/" in f or f.endswith(".yml")}, set()
        )

    def test_last_version_starts_at_zero_or_at_the_newest_tag(self):
        fresh = self.tmp_path / "fresh"
        fresh.mkdir()
        (fresh / "pyproject.toml").write_text('[project]\nname = "fresh"\n')
        git(fresh, "init", "-q")
        installer.install(fresh)
        self.assertEqual((fresh / "LAST_VERSION").read_text(), "0.0.0\n")

        tagged = self.tmp_path / "tagged"
        tagged.mkdir()
        (tagged / "pyproject.toml").write_text('[project]\nname = "tagged"\n')
        git(tagged, "init", "-q")
        git(tagged, "commit", "-q", "--allow-empty", "-m", "chore: first")
        git(tagged, "tag", "v2.3.4")
        installer.install(tagged)
        self.assertEqual((tagged / "LAST_VERSION").read_text(), "2.3.4\n")


class HooksTest(InstallCase):
    def test_own_hooks_are_refreshed(self):
        installer.install(self.repo)
        (self.repo / ".git/hooks/pre-commit").write_text(
            "# action-platform hook\nbroken"
        )

        installer.install(self.repo)

        self.assertIn(
            "gitflow_check branch", (self.repo / ".git/hooks/pre-commit").read_text()
        )

    def test_existing_hooks_are_kept_and_chained(self):
        hooks = self.repo / ".git/hooks"
        hooks.mkdir(exist_ok=True)
        (hooks / "pre-commit").write_text("#!/bin/sh\necho husky > .ran\n")
        (hooks / "pre-commit").chmod(0o755)

        plan = installer.install(self.repo)

        self.assertEqual(plan.hooks_preserved, ["pre-commit"])
        self.assertIn("gitflow_check branch", (hooks / "pre-commit").read_text())
        self.assertTrue(
            (hooks / "pre-commit.pre-action-platform")
            .read_text()
            .startswith("#!/bin/sh")
        )

        git(self.repo, "checkout", "-q", "-b", "feature/9")
        subprocess.run([str(hooks / "pre-commit")], cwd=self.repo, check=True)
        self.assertEqual((self.repo / ".ran").read_text().strip(), "husky")

        installer.install(self.repo)
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

        plan = installer.install(self.repo)

        self.assertFalse(plan.hooks_installed)
        self.assertIn("versioned", plan.hooks_skipped or "")
        self.assertEqual(
            (self.repo / ".husky" / "pre-commit").read_text(), "#!/bin/sh\n"
        )
        self.assertFalse((self.repo / ".git/hooks/gitflow.sh").exists())


class CiFollowsTheRemoteTest(TempCase):
    def test_a_gitlab_remote_gets_gitlab_ci(self):
        from tests.support import git, template_repo

        self.setenv(
            "ACTION_PLATFORM_TEMPLATES", str(template_repo(self.tmp_path / "official"))
        )
        repo = self.tmp_path / "svc"
        repo.mkdir()
        (repo / "pyproject.toml").write_text('[project]\nname = "svc"\n')
        git(repo, "init", "-q", "-b", "main")
        git(repo, "remote", "add", "origin", "https://gitlab.com/acme/svc.git")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "chore: init")

        plan = installer.install(repo)

        self.assertEqual(plan.ci, "gitlab")
        self.assertIn(".gitlab-ci.yml", plan.created)
        self.assertFalse(any(".github" in f for f in plan.created))

    def test_a_bitbucket_remote_gets_bitbucket_pipelines(self):
        from tests.support import git, template_repo

        self.setenv(
            "ACTION_PLATFORM_TEMPLATES", str(template_repo(self.tmp_path / "official"))
        )
        repo = self.tmp_path / "svc"
        repo.mkdir()
        (repo / "pyproject.toml").write_text('[project]\nname = "svc"\n')
        git(repo, "init", "-q", "-b", "main")
        git(repo, "remote", "add", "origin", "https://bitbucket.org/acme/svc.git")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "chore: init")

        plan = installer.install(repo)

        self.assertEqual(plan.ci, "bitbucket")
        self.assertIn("bitbucket-pipelines.yml", plan.created)


class ExistingCiTest(InstallCase):
    def setUp(self):
        super().setUp()
        (self.repo / ".github/workflows/code-quality.yml").unlink()
        (self.repo / ".github/workflows").rmdir()
        (self.repo / ".github").rmdir()

    def test_a_jenkinsfile_keeps_github_workflows_out(self):
        (self.repo / "Jenkinsfile").write_text("pipeline {}\n")

        plan = installer.install(self.repo, dry_run=True)

        self.assertEqual(plan.ci, "jenkins")
        self.assertEqual(plan.detected_ci, ["jenkins"])
        self.assertEqual(plan.warnings, [])
        self.assertEqual((self.repo / "Jenkinsfile").read_text(), "pipeline {}\n")
        self.assertFalse(any(".github" in f for f in plan.created))

    def test_a_kept_jenkinsfile_gets_the_stages_that_run_the_checks(self):
        (self.repo / "Jenkinsfile").write_text("pipeline {}\n")

        plan = installer.install(self.repo, dry_run=True)

        self.assertIn("ci-jenkins@v1", plan.ci_snippet)
        self.assertIn("apCheck(language: 'python')", plan.ci_snippet)
        self.assertIn("apConventionalCommit()", plan.ci_snippet)
        self.assertIn("apGitflow()", plan.ci_snippet)
        self.assertEqual(
            installer.install(self.repo, ci="github", dry_run=True).ci_snippet, ""
        )

    def test_gitlab_and_bitbucket_files_are_detected(self):
        (self.repo / ".gitlab-ci.yml").write_text("stages: []\n")
        self.assertEqual(installer.install(self.repo, dry_run=True).ci, "gitlab")

        (self.repo / ".gitlab-ci.yml").unlink()
        (self.repo / "bitbucket-pipelines.yml").write_text("pipelines: {}\n")
        self.assertEqual(installer.install(self.repo, dry_run=True).ci, "bitbucket")

    def test_two_cis_need_a_choice(self):
        (self.repo / "Jenkinsfile").write_text("pipeline {}\n")
        (self.repo / ".github/workflows").mkdir(parents=True)
        (self.repo / ".github/workflows/deploy.yaml").write_text("on: push\n")

        with self.assertRaisesRegex(InstallError, "Jenkinsfile, .github/workflows"):
            installer.install(self.repo, dry_run=True)

        plan = installer.install(self.repo, ci="jenkins", dry_run=True)
        self.assertEqual(plan.ci, "jenkins")
        self.assertEqual(
            plan.warnings,
            [
                ".github/workflows found; installing jenkins CI files runs a second CI next to it"
            ],
        )

    def test_the_flag_wins_with_a_warning(self):
        (self.repo / "Jenkinsfile").write_text("pipeline {}\n")

        plan = installer.install(self.repo, ci="github", dry_run=True)

        self.assertEqual(plan.ci, "github")
        self.assertIn(".github/workflows/gitflow.yml", plan.created)
        self.assertIn("Jenkinsfile found", plan.warnings[0])
        self.assertEqual(
            installer.install(self.repo, ci="none", dry_run=True).warnings, []
        )

    def test_platform_toml_ci_wins_over_files(self):
        (self.repo / ".github/workflows").mkdir(parents=True)
        (self.repo / ".github/workflows/build.yml").write_text("on: push\n")
        (self.repo / "Jenkinsfile").write_text("pipeline {}\n")
        (self.repo / "platform.toml").write_text(
            '[project]\nname = "x"\nci = "jenkins"\nlanguage = "python"\n'
        )

        plan = installer.install(self.repo, dry_run=True)

        self.assertEqual(plan.ci, "jenkins")
        self.assertFalse(any(".github" in f for f in plan.created))


class SourceHostTest(unittest.TestCase):
    def test_remotes(self):
        cases = {
            "git@github.com:acme/app.git": ("github", "acme/app", ""),
            "https://github.com/acme/app": ("github", "acme/app", ""),
            "https://gitlab.com/acme/group/app.git": (
                "gitlab",
                "acme/group/app",
                "",
            ),
            "git@gitlab.example.com:team/app.git": (
                "gitlab",
                "team/app",
                "https://gitlab.example.com",
            ),
            "ssh://git@bitbucket.org/acme/app.git": ("bitbucket", "acme/app", ""),
            "https://git.example.com/acme/app.git": ("", "", ""),
            "": ("", "", ""),
        }

        for remote, expected in cases.items():
            self.assertEqual(installer._source_host(remote), expected, remote)

    def test_platform_toml_names_a_self_hosted_gitlab(self):
        repo = mock.Mock()
        repo.remote_url.return_value = "https://gitlab.example.com/team/app.git"

        text = installer._platform_toml(repo, "web", "python", "gitlab")

        self.assertIn(
            '[source_host]\nkind = "gitlab"\nrepo = "team/app"\nbase_url = "https://gitlab.example.com"\n',
            text,
        )


class SeedVersionTest(TempCase):
    def setUp(self):
        super().setUp()
        self.repo = self.tmp_path / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "chore: first")

    def seed(self, *tags: str) -> str:
        for tag in tags:
            git(self.repo, "tag", tag)

        return installer._seed_version(Repository(self.repo))

    def test_never_released(self):
        self.assertEqual(self.seed(), "0.0.0")
        self.assertEqual(self.seed("latest", "api/v1.0.0", "release-2"), "0.0.0")

    def test_unprefixed_tags(self):
        self.assertEqual(self.seed("1.2.3", "1.10.0", "1.9.9"), "1.10.0")

    def test_mixed_prefixes(self):
        self.assertEqual(self.seed("v3.4.1", "3.4.2"), "3.4.2")

    def test_a_pre_release_counts_until_a_stable_follows_it(self):
        self.assertEqual(
            self.seed("v1.9.0", "v2.0.0-rc.1", "v2.0.0-rc.2"), "2.0.0-rc.2"
        )
        self.assertEqual(self.seed("v2.0.0"), "2.0.0")

    def test_pre_releases_compare_numerically(self):
        self.assertEqual(self.seed("v2.0.0-rc.2", "v2.0.0-rc.10"), "2.0.0-rc.10")

    def test_tags_off_the_current_branch_count(self):
        git(self.repo, "checkout", "-q", "-b", "develop")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "feat: x")
        git(self.repo, "checkout", "-q", "main")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "fix: y")
        git(self.repo, "tag", "v1.4.0")
        git(self.repo, "checkout", "-q", "develop")

        self.assertEqual(self.seed(), "1.4.0")
