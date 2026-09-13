"""action_platform.core.flow.workflow — pull request proposals from a git-flow branch and opening through the host."""

from __future__ import annotations

from action_platform.core.context import PRRef
from action_platform.core.flow import workflow
from action_platform.core.flow.workflow import GitFlow, PullRequestError
from tests.support import TempCase, git, repo_with_origin


class PullRequestTest(TempCase):
    def setUp(self):
        super().setUp()
        self.repo = repo_with_origin(
            self.tmp_path, files={}, message="chore: bootstrap"
        )
        git(self.repo, "checkout", "-qb", "develop")
        git(self.repo, "push", "-q", "-u", "origin", "develop")
        git(self.repo, "checkout", "-qb", "feature/7-login")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "feat(login): form")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "test(login): cover form")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "fix(login): trim email")

    def test_proposal_targets_develop_and_describes_commits(self):
        proposal = GitFlow(self.repo).propose()

        self.assertEqual(proposal.head, "feature/7-login")
        self.assertEqual(proposal.base, "develop")
        self.assertEqual(proposal.title, "feat(login): form")
        self.assertIn("### Features", proposal.body)
        self.assertIn("**login:** form", proposal.body)
        self.assertIn("### Bug Fixes", proposal.body)
        self.assertEqual(len(proposal.commits), 3)

    def test_hotfix_targets_main(self):
        git(self.repo, "checkout", "-q", "main")
        git(self.repo, "checkout", "-qb", "hotfix/9")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "fix: prod is down")

        self.assertEqual(GitFlow(self.repo).propose().base, "main")

    def test_refuses_wrong_target_and_protected_head(self):
        with self.assertRaisesRegex(PullRequestError, "may not merge"):
            GitFlow(self.repo).propose(base="main")

        git(self.repo, "checkout", "-q", "main")

        with self.assertRaisesRegex(PullRequestError, "protected"):
            GitFlow(self.repo).propose()

    def test_refuses_bad_commits(self):
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "wip")

        with self.assertRaisesRegex(PullRequestError, "git-flow"):
            GitFlow(self.repo).propose()

    def test_open_pushes_and_calls_host(self):
        (self.repo / "platform.toml").write_text(
            '[project]\nname = "x"\n[source_host]\nkind = "github"\nrepo = "acme/x"\n'
        )
        git(self.repo, "add", "platform.toml")
        git(self.repo, "commit", "-q", "-m", "chore(platform): install")
        calls: dict = {}

        class Host:
            name = "fake"
            repo = "acme/x"

            def open_pr(self, ctx, base, head, title, body, draft=False):
                calls.update(base=base, head=head, title=title, draft=draft)
                return PRRef(number=1, url="https://example.com/pr/1")

        self.patch(
            workflow.Config,
            "from_toml",
            classmethod(lambda cls, p: type("C", (), {"source_host": Host()})()),
        )

        ref = GitFlow(self.repo).open_pr(draft=True)

        self.assertEqual(ref.number, 1)
        self.assertEqual(
            calls,
            {
                "base": "develop",
                "head": "feature/7-login",
                "title": "feat(login): form",
                "draft": True,
            },
        )
        self.assertIn(
            "feature/7-login", git(self.repo, "ls-remote", "--heads", "origin")
        )
