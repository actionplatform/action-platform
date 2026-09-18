"""CI runners: where builds run. One module per provider, chosen by `kind`."""

from __future__ import annotations

from action_platform.abc.ci_runner import CIRunner
from action_platform.core.exception import ConfigError
from action_platform.providers.ci.github_actions import CIGithubActions
from action_platform.providers.ci.jenkins import CIJenkins
from action_platform.providers.ci.none import CINone

CI_KINDS = ("github_actions", "jenkins", "none")

EMBEDDED_CI = {
    "github": "github_actions",
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
    if kind == "github_actions":
        return CIGithubActions(repo=repo or "", token=token, base_url=base_url)

    if kind == "jenkins":
        return CIJenkins(base_url=base_url or "", token=token, username=username)

    if kind in ("none", "", None):
        return CINone()

    raise ConfigError(f"unknown ci kind: {kind} (available: {', '.join(CI_KINDS)})")


__all__ = ["CI_KINDS", "EMBEDDED_CI", "build_ci_runner", "embedded_ci_kind"]
