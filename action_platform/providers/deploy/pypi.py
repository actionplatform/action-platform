"""PyPI: a release is there when the JSON API knows the version."""

from __future__ import annotations

from action_platform.core.exception import ConfigError
from action_platform.providers.deploy.observed import ObservedTarget


class DeployPypi(ObservedTarget):
    """
    Args:
        package (str): the distribution name on the index.
        index_url (str | None): another index, e.g. https://test.pypi.org; default pypi.org.
    """

    name = "pypi"

    def __init__(
        self, package: str = "", index_url: str | None = None, **_: object
    ) -> None:
        if not package:
            raise ConfigError("pypi target needs a package")

        self.package = package
        self.index = (index_url or "https://pypi.org").rstrip("/")

    def verify(self, version: str, stage: str | None = None) -> bool:
        return self._exists(f"{self.index}/pypi/{self.package}/{version}/json")

    def url(self, version: str, stage: str | None = None) -> str | None:
        return f"{self.index}/project/{self.package}/{version}/"
