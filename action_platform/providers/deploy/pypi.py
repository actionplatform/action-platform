"""PyPI: a release is there when the JSON API knows the version."""

from __future__ import annotations

from action_platform.core.exception import ConfigError
from action_platform.providers.deploy.observed import ObservedTarget


TEST_INDEX = "https://test.pypi.org"


class DeployPypi(ObservedTarget):
    """
    Args:
        package (str): the distribution name on the index.
        index_url (str | None): another index; default pypi.org. A `test` scope always goes to test.pypi.org.
    """

    name = "pypi"

    def __init__(
        self, package: str = "", index_url: str | None = None, **_: object
    ) -> None:
        if not package:
            raise ConfigError("pypi target needs a package")

        self.package = package
        self.index = (index_url or "https://pypi.org").rstrip("/")

    def registry_for(self, criticality: str) -> str:
        return "testpypi" if criticality == "test" else "pypi"

    def _index(self, stage: str | None) -> str:
        return TEST_INDEX if stage == "testpypi" else self.index

    def verify(self, version: str, stage: str | None = None) -> bool:
        return self._exists(f"{self._index(stage)}/pypi/{self.package}/{version}/json")

    def url(self, version: str, stage: str | None = None) -> str | None:
        return f"{self._index(stage)}/project/{self.package}/{version}/"
