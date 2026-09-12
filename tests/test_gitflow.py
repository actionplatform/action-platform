"""Git-flow rules."""

from action_platform.core import gitflow


def test_branch_names():
    assert gitflow.check_branch("feature/42-login") is None
    assert gitflow.check_branch("main") is None
    assert gitflow.check_branch("wip") is not None
    assert gitflow.check_branch("fix/1") is not None


def test_commit_messages():
    assert gitflow.check_commit("feat(api): x") is None
    assert gitflow.check_commit("Merge branch 'x'") is None
    assert gitflow.check_commit("update stuff") is not None
    assert gitflow.check_commit("Feat: caps") is not None


def test_protected_branches():
    assert gitflow.check_protected("feature/1", "feat: x") is None
    assert gitflow.check_protected("main", "chore(release): 1.0.0") is None
    assert (
        gitflow.check_protected("main", "chore: bootstrap project from action-platform")
        is None
    )
    assert gitflow.check_protected("main", "feat: x") is not None
    assert gitflow.check_protected("develop", "fix: y") is not None


def test_targets():
    assert gitflow.check_target("feature/1", "develop", "main", True) is None
    assert gitflow.check_target("feature/1", "main", "main", False) is None
    assert gitflow.check_target("feature/1", "main", "main", True) is not None
    assert gitflow.check_target("hotfix/1", "main", "main", True) is None
    assert gitflow.check_target("hotfix/1", "develop", "main", True) is None
    assert gitflow.check_target("release/1.0", "main", "main", True) is None
    assert gitflow.check_target("develop", "main", "main", True) is None
    assert gitflow.check_target("main", "develop", "main", True) is not None
    assert gitflow.check_target("support/1", "main", "main", True) is not None
