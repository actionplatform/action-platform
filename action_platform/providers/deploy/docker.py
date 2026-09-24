"""A container registry: a release is there when the tag has a manifest.

Registries that need a token (GHCR, Docker Hub) hand one out anonymously
for public images through the `www-authenticate` challenge; private images
take `token` (or `AP_DOCKER_TOKEN`).
"""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request

from action_platform.core.exception import ConfigError, ProviderError
from action_platform.providers.deploy.pipeline_published import PipelinePublishedTarget

MANIFESTS = ", ".join(
    [
        "application/vnd.docker.distribution.manifest.v2+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.oci.image.index.v1+json",
    ]
)


class DeployDocker(PipelinePublishedTarget):
    """
    Args:
        image (str): `registry/namespace/name`, e.g. ghcr.io/actionplatform/api; a bare `name` means Docker Hub's library.
        tag_prefix (str): what precedes the version in the tag, e.g. "v"; default none.
        token (str | None): a registry token for private images.
    """

    name = "docker"

    def __init__(
        self,
        image: str = "",
        tag_prefix: str = "",
        token: str | None = None,
        username: str | None = None,
        **_: object,
    ) -> None:
        if not image:
            raise ConfigError("docker target needs an image")

        self.registry, self.repository = self._split(image)
        self.image = image
        self.tag_prefix = tag_prefix
        self.token = token or os.getenv("AP_DOCKER_TOKEN")
        self.username = username

    @staticmethod
    def _split(image: str) -> tuple[str, str]:
        first, _, rest = image.partition("/")

        if rest and ("." in first or ":" in first or first == "localhost"):
            registry, repository = first, rest
        else:
            registry, repository = "registry-1.docker.io", image

        if registry == "docker.io":
            registry = "registry-1.docker.io"

        if registry == "registry-1.docker.io" and "/" not in repository:
            repository = f"library/{repository}"

        return registry, repository

    def _headers(self) -> dict[str, str]:
        if self.token and self.username:
            raw = base64.b64encode(f"{self.username}:{self.token}".encode()).decode()

            return {"authorization": f"Basic {raw}"}

        if self.token:
            return {"authorization": f"Bearer {self.token}"}

        return {}

    def _anonymous(self, challenge: str) -> dict[str, str]:
        params = dict(re.findall(r'(\w+)="([^"]*)"', challenge))
        realm = params.get("realm")

        if not realm:
            return {}

        query = "&".join(
            f"{k}={v}" for k, v in params.items() if k in ("service", "scope")
        )
        req = urllib.request.Request(
            f"{realm}?{query}", headers={"user-agent": "action-platform"}
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                token = json.loads(res.read()).get("token") or ""
        except (urllib.error.URLError, ValueError):
            return {}

        return {"authorization": f"Bearer {token}"} if token else {}

    def verify(self, version: str, stage: str | None = None) -> bool:
        url = f"https://{self.registry}/v2/{self.repository}/manifests/{self.tag_prefix}{version}"
        headers = {"accept": MANIFESTS, **self._headers()}

        for attempt in range(2):
            req = urllib.request.Request(
                url, method="HEAD", headers={"user-agent": "action-platform", **headers}
            )

            try:
                with urllib.request.urlopen(req, timeout=30) as res:
                    return 200 <= res.status < 300
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return False

                if e.code == 401 and attempt == 0 and not self.token:
                    headers.update(
                        self._anonymous(e.headers.get("www-authenticate", ""))
                    )
                    continue

                if e.code in (401, 403):
                    return False

                raise ProviderError(f"HEAD {url} → {e.code}") from e
            except urllib.error.URLError as e:
                raise ProviderError(f"cannot reach {url}: {e.reason}") from e

        return False

    def url(self, version: str, stage: str | None = None) -> str | None:
        tag = f"{self.tag_prefix}{version}"

        if self.registry == "ghcr.io":
            owner, _, name = self.repository.partition("/")

            return f"https://github.com/{owner}/{name.split('/')[0]}/pkgs/container/{name.replace('/', '%2F')}"

        if self.registry == "registry-1.docker.io":
            return f"https://hub.docker.com/r/{self.repository}/tags?name={tag}"

        return None
