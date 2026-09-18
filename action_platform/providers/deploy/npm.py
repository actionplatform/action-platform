"""npm: a release is there when the registry answers for the version."""

from __future__ import annotations

from urllib.parse import quote

from action_platform.core.exception import ConfigError
from action_platform.providers.deploy.observed import ObservedTarget


class DeployNpm(ObservedTarget):
    """
    Args:
        package (str): the package name, scoped or not.
        registry (str | None): another registry; default registry.npmjs.org.
    """

    name = "npm"

    def __init__(
        self, package: str = "", registry: str | None = None, **_: object
    ) -> None:
        if not package:
            raise ConfigError("npm target needs a package")

        self.package = package
        self.registry = (registry or "https://registry.npmjs.org").rstrip("/")

    def verify(self, version: str, stage: str | None = None) -> bool:
        return self._exists(
            f"{self.registry}/{quote(self.package, safe='@')}/{version}"
        )

    def url(self, version: str, stage: str | None = None) -> str | None:
        return f"https://www.npmjs.com/package/{self.package}/v/{version}"
