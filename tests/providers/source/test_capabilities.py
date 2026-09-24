"""action_platform.abc.source_host — which capability protocols each built-in host satisfies."""

from __future__ import annotations

import unittest
from pathlib import Path

from action_platform.abc.source_host import (
    ListsPullRequests,
    PublishesReleases,
    SupportsRepoCreation,
    SupportsRepoDeletion,
)
from action_platform.core.context import Context
from action_platform.core.exception import ProviderError
from action_platform.providers.source import build_source_host

CAPABILITIES = (
    SupportsRepoCreation,
    SupportsRepoDeletion,
    PublishesReleases,
    ListsPullRequests,
)


class CapabilitiesTest(unittest.TestCase):
    def test_hosted_providers_offer_every_capability(self):
        for kind in ("github", "gitlab", "bitbucket"):
            host = build_source_host(kind, "acme/x", token="t", username="ada")

            for capability in CAPABILITIES:
                self.assertIsInstance(host, capability, f"{kind} {capability}")

    def test_a_generic_server_offers_none(self):
        host = build_source_host("generic", "acme/x", base_url="https://git.acme.io")

        for capability in CAPABILITIES:
            self.assertNotIsInstance(host, capability)

    def test_a_generic_server_refuses_pull_requests_with_a_provider_error(self):
        host = build_source_host("generic", "acme/x", base_url="https://git.acme.io")

        with self.assertRaises(ProviderError):
            host.open_pr(Context(repo_root=Path(".")), "main", "feature/1", "t", "b")
