"""CI runners: where builds run. The embedded ones live here, one module per provider; a CI server of its own comes from the plugin that registers it in the `action_platform.ci_runner` entry-point group."""

from __future__ import annotations

from action_platform.abc.ci_runner import CIRunner
from action_platform.core import module
from action_platform.core.exception import ConfigError
from action_platform.providers.ci.bitbucket_pipelines import CIBitbucket
from action_platform.providers.ci.github_actions import CIGithubActions
from action_platform.providers.ci.gitlab_ci import CIGitlab
from action_platform.providers.ci.none import CINone
from action_platform.providers.registry import ProviderRegistry

CI_RUNNERS: ProviderRegistry[CIRunner] = ProviderRegistry("ci")
CI_RUNNERS.register(CIGithubActions)
CI_RUNNERS.register(CIGitlab)
CI_RUNNERS.register(CIBitbucket)
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


def ci_kinds() -> tuple[str, ...]:
    """The built-in kinds and those the installed plugins register."""
    return tuple(dict.fromkeys((*CI_RUNNERS.kinds(), *module.load_ci_runners())))


def build_ci_runner(
    kind: str,
    base_url: str | None = None,
    token: str | None = None,
    username: str | None = None,
    repo: str | None = None,
) -> CIRunner:
    """A CIRunner for `kind`. Embedded kinds take the source host's `repo` and `token`; servers, brought by their plugin, take their own `base_url`, `username` and `token`."""
    kind = kind or "none"
    args = {"repo": repo or "", "token": token, "username": username}

    if kind in CI_RUNNERS.classes:
        return CI_RUNNERS.build(kind, base_url=base_url, **args)

    plugins = module.load_ci_runners()

    if kind not in plugins:
        raise ConfigError(
            f"no CI runner {kind!r} is installed (available: {', '.join(ci_kinds())}); "
            f"a CI server comes from its plugin — install apx-{kind}"
        )

    registry: ProviderRegistry[CIRunner] = ProviderRegistry("ci")
    registry.classes[kind] = plugins[kind]

    return registry.build(kind, base_url=base_url, **args)


__all__ = [
    "CI_KINDS",
    "CI_RUNNERS",
    "EMBEDDED_CI",
    "build_ci_runner",
    "ci_kinds",
    "embedded_ci_kind",
]
