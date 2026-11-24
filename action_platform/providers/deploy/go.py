"""Go modules: a release is there when the module proxy knows the version."""

from __future__ import annotations

import re

from action_platform.core.exception import ConfigError
from action_platform.providers.deploy.pipeline_published import PipelinePublishedTarget


class DeployGo(PipelinePublishedTarget):
    """
    Args:
        module (str): the module path, e.g. github.com/acme/sdk.
    """

    name = "go"

    def __init__(self, module: str = "", **_: object) -> None:
        if not module:
            raise ConfigError("go target needs a module")

        self.module = module.strip("/")

    @staticmethod
    def escape(path: str) -> str:
        """The proxy's case encoding: every capital letter becomes `!` and its lowercase."""
        return re.sub(r"[A-Z]", lambda m: "!" + m.group(0).lower(), path)

    def verify(self, version: str, stage: str | None = None) -> bool:
        return self._exists(
            f"https://proxy.golang.org/{self.escape(self.module)}/@v/{self.escape('v' + version)}.info"
        )

    def url(self, version: str, stage: str | None = None) -> str | None:
        return f"https://pkg.go.dev/{self.module}@v{version}"
