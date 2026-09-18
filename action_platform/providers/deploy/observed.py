"""What a target someone else's pipeline publishes to shares: no deploy steps, a destination to ask."""

from __future__ import annotations

import urllib.error
import urllib.request

from action_platform.abc.deploy_target import DeployTarget
from action_platform.core.context import Context, DeployResult
from action_platform.core.exception import DeployError, ProviderError


class ObservedTarget(DeployTarget):
    name: str

    def preflight(self, ctx: Context) -> None:
        raise DeployError(
            f"{self.name} is published by a pipeline outside the platform; the platform only verifies it"
        )

    def deploy(self, ctx: Context) -> DeployResult:
        raise DeployError(
            f"{self.name} is published by a pipeline outside the platform; the platform only verifies it"
        )

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
