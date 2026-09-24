"""What a target someone else's pipeline publishes to shares: no deploy steps, a destination to ask."""

from __future__ import annotations

import urllib.error
import urllib.request

from action_platform.abc.deploy_target import DeployTarget
from action_platform.core.context import Check, Context, DeployResult
from action_platform.core.exception import DeployError, ProviderError


class PipelinePublishedTarget(DeployTarget):
    name: str

    def registry_for(self, criticality: str) -> str:
        """Where a scope of `criticality` publishes: the registry itself, or its test counterpart for a `test` scope, when the kind has one."""
        return self.name

    def preflight(self, ctx: Context) -> None:
        raise DeployError(
            f"{self.name} is published by a pipeline outside the platform; the platform only verifies it"
        )

    def deploy(self, ctx: Context) -> DeployResult:
        raise DeployError(
            f"{self.name} is published by a pipeline outside the platform; the platform only verifies it"
        )

    def readiness(self, ctx: Context) -> list[Check]:
        version = ctx.next_version

        try:
            published = self.verify(version, ctx.stage)
        except ProviderError as e:
            return [
                Check(
                    "destination.reachable",
                    False,
                    str(e),
                    severity="warning",
                    fix="the registry did not answer; check the network or the package name",
                )
            ]

        where = self.url(version, ctx.stage) or self.name

        return [
            Check(
                "destination.version",
                not published,
                f"{version} is already at {where}"
                if published
                else f"{version} is not yet at {self.name}",
                fix="publishing the same version twice fails; cut a new release"
                if published
                else None,
            )
        ]

    @staticmethod
    def _exists(url: str, headers: dict[str, str] | None = None) -> bool:
        req = urllib.request.Request(
            url,
            method="GET",
            headers={"user-agent": "action-platform", **(headers or {})},
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return 200 <= res.status < 300
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 404):
                return False

            raise ProviderError(f"GET {url} → {e.code}") from e
        except urllib.error.URLError as e:
            raise ProviderError(f"cannot reach {url}: {e.reason}") from e
