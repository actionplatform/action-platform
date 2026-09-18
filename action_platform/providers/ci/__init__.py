"""CI runners: where an app's builds and pipelines run. One module per provider, chosen by `kind`."""

from action_platform.abc.ci_runner import CIRunner
from action_platform.providers.ci.factory import (
    CI_KINDS,
    EMBEDDED_CI,
    build_ci_runner,
    embedded_ci_kind,
)

__all__ = ["CI_KINDS", "EMBEDDED_CI", "CIRunner", "build_ci_runner", "embedded_ci_kind"]
