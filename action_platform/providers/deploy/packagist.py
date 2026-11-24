"""Packagist: a release is there when the package's metadata lists the version."""

from __future__ import annotations

from action_platform.core.exception import ConfigError
from action_platform.providers.deploy.pipeline_published import PipelinePublishedTarget


class DeployPackagist(PipelinePublishedTarget):
    """
    Args:
        package (str): the Composer package, `vendor/name`.
    """

    name = "packagist"

    def __init__(self, package: str = "", **_: object) -> None:
        if not package or "/" not in package:
            raise ConfigError("packagist target needs a package as vendor/name")

        self.package = package.lower()

    def verify(self, version: str, stage: str | None = None) -> bool:
        found = self._json(f"https://repo.packagist.org/p2/{self.package}.json") or {}
        listed = (found.get("packages") or {}).get(self.package) or []

        return any(
            str(entry.get("version") or "").removeprefix("v") == version
            for entry in listed
        )

    def url(self, version: str, stage: str | None = None) -> str | None:
        return f"https://packagist.org/packages/{self.package}"
