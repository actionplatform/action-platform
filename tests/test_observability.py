"""action_platform.observability — Sentry starts from the config it is handed."""

from unittest import mock

from action_platform import observability
from action_platform.options import ObservabilityConfig
from tests.support import TempCase


class ObserveTest(TempCase):
    def setUp(self):
        super().setUp()
        self.sdk = mock.Mock()
        self.patch(observability, "sentry_sdk", self.sdk)

    def test_the_environment_is_not_consulted(self):
        self.setenv("AP_SENTRY_DSN", "https://key@o1.ingest.sentry.io/1")

        self.assertFalse(observability.observe("cli", ObservabilityConfig()))
        self.sdk.init.assert_not_called()

    def test_the_config_decides_dsn_environment_and_sampling(self):
        config = ObservabilityConfig(
            dsn="https://key@o1.ingest.sentry.io/1",
            environment="staging",
            traces_sample_rate=0.5,
        )

        self.assertTrue(observability.observe("mcp", config, version="1.2.3"))

        kwargs = self.sdk.init.call_args.kwargs
        self.assertEqual(kwargs["dsn"], "https://key@o1.ingest.sentry.io/1")
        self.assertEqual(kwargs["environment"], "staging")
        self.assertEqual(kwargs["traces_sample_rate"], 0.5)
        self.assertEqual(kwargs["release"], "mcp@1.2.3")
        self.sdk.set_tag.assert_called_once_with("component", "mcp")

    def test_without_the_sdk_nothing_starts(self):
        self.patch(observability, "sentry_sdk", None)

        self.assertFalse(
            observability.observe("cli", ObservabilityConfig(dsn="https://k@o/1"))
        )
