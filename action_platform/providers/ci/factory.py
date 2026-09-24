"""CI runners: where builds run. One module per provider, chosen by `kind`."""

from __future__ import annotations

from action_platform.abc.ci_runner import CIRunner
from action_platform.providers.ci.bitbucket_pipelines import CIBitbucket
from action_platform.providers.ci.github_actions import CIGithubActions
from action_platform.providers.ci.gitlab_ci import CIGitlab
from action_platform.providers.ci.jenkins import CIJenkins
from action_platform.providers.ci.none import CINone
from action_platform.providers.registry import ProviderRegistry

CI_RUNNERS: ProviderRegistry[CIRunner] = ProviderRegistry("ci")
CI_RUNNERS.register(CIGithubActions)
CI_RUNNERS.register(CIGitlab)
CI_RUNNERS.register(CIBitbucket)
CI_RUNNERS.register(CIJenkins)
CI_RUNNERS.register(CINone)

CI_KINDS = CI_RUNNERS.kinds()

EMBEDDED_CI = {
    "github": "github_actions",
    "gitlab": "gitlab_ci",
    "bitbucket": "bitbucket_pipelines",
}


def embedded_ci_kind(source_kind: str | None) -> str:
    """The CI that lives inside a source host of `source_kind`, or "none"."""
    return EMBEDDED_CI.get(source_kind or "", "none")


def build_ci_runner(
    kind: str,
    base_url: str | None = None,
    token: str | None = None,
    username: str | None = None,
    repo: str | None = None,
) -> CIRunner:
    """A CIRunner for `kind`. Embedded kinds take the source host's `repo` and `token`; servers take their own `base_url`, `username` and `token`."""
    return CI_RUNNERS.build(
        kind or "none",
        repo=repo or "",
        token=token,
        username=username,
        base_url=base_url,
    )


__all__ = [
    "CI_KINDS",
    "CI_RUNNERS",
    "EMBEDDED_CI",
    "build_ci_runner",
    "embedded_ci_kind",
]
