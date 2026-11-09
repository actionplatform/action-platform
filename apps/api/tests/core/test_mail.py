"""app.core.shared.mail — SMTP configuration from the environment and one message per connection, no network."""

from __future__ import annotations

import smtplib
import unittest
from unittest import mock

from action_platform.core.exception import ConfigError, ProviderError
from action_platform.testing.fixtures import TempCase

from app.core.shared.mail import Mail, SmtpConfig, SmtpMailer, mailer_from_env


class SmtpConfigTest(unittest.TestCase):
    def test_defaults_to_starttls_on_587(self):
        config = SmtpConfig.from_env({"AP_SMTP_HOST": "smtp.example.com"})

        self.assertEqual(config.port, 587)
        self.assertEqual(config.security, "starttls")
        self.assertTrue(config.configured)

    def test_ssl_defaults_to_465(self):
        config = SmtpConfig.from_env(
            {"AP_SMTP_HOST": "smtp.example.com", "AP_SMTP_SECURITY": "SSL"}
        )

        self.assertEqual(config.port, 465)
        self.assertEqual(config.security, "ssl")

    def test_rejects_an_unknown_security(self):
        with self.assertRaises(ConfigError):
            SmtpConfig.from_env({"AP_SMTP_SECURITY": "tls"})

    def test_no_host_means_no_mailer(self):
        self.assertIsNone(mailer_from_env({}))

    def test_mailer_needs_a_sender(self):
        with self.assertRaises(ConfigError):
            mailer_from_env({"AP_SMTP_HOST": "smtp.example.com"})


class SmtpPasswordFileTest(TempCase):
    def test_reads_the_password_from_a_file(self):
        path = self.tmp_path / "smtp-password"
        path.write_text("s3cret\n")

        config = SmtpConfig.from_env(
            {"AP_SMTP_HOST": "smtp.example.com", "AP_SMTP_PASSWORD_FILE": str(path)}
        )

        self.assertEqual(config.password, "s3cret")


class SmtpMailerTest(unittest.TestCase):
    def config(self, **extra) -> SmtpConfig:
        fields = {
            "host": "smtp.example.com",
            "user": "mailer",
            "password": "pw",
            "sender": "Action Platform <no-reply@example.com>",
            **extra,
        }

        return SmtpConfig(**fields)

    def test_starttls_logs_in_and_sends_text_and_html(self):
        with mock.patch("app.core.shared.mail.smtplib.SMTP") as smtp_class:
            smtp = smtp_class.return_value
            smtp.__enter__.return_value = smtp

            SmtpMailer(self.config()).send(
                Mail("ana@example.com", "Reset", "plain body", "<p>html body</p>")
            )

        smtp_class.assert_called_once_with("smtp.example.com", 587, timeout=15)
        smtp.starttls.assert_called_once()
        smtp.login.assert_called_once_with("mailer", "pw")
        message = smtp.send_message.call_args.args[0]
        self.assertEqual(message["To"], "ana@example.com")
        self.assertEqual(message["Subject"], "Reset")
        self.assertEqual(message["From"], "Action Platform <no-reply@example.com>")
        self.assertIn("plain body", message.get_body(("plain",)).get_content())
        self.assertIn("html body", message.get_body(("html",)).get_content())

    def test_ssl_uses_an_implicit_tls_connection(self):
        with mock.patch("app.core.shared.mail.smtplib.SMTP_SSL") as smtp_class:
            smtp = smtp_class.return_value
            smtp.__enter__.return_value = smtp

            SmtpMailer(self.config(security="ssl", port=465)).send(
                Mail("ana@example.com", "Hi", "body")
            )

        self.assertEqual(smtp_class.call_args.args, ("smtp.example.com", 465))
        smtp.starttls.assert_not_called()
        smtp.send_message.assert_called_once()

    def test_without_user_skips_login(self):
        with mock.patch("app.core.shared.mail.smtplib.SMTP") as smtp_class:
            smtp = smtp_class.return_value
            smtp.__enter__.return_value = smtp

            SmtpMailer(self.config(user="", security="none")).send(
                Mail("ana@example.com", "Hi", "body")
            )

        smtp.starttls.assert_not_called()
        smtp.login.assert_not_called()

    def test_a_refused_message_is_a_provider_error(self):
        with mock.patch("app.core.shared.mail.smtplib.SMTP") as smtp_class:
            smtp = smtp_class.return_value
            smtp.__enter__.return_value = smtp
            smtp.send_message.side_effect = smtplib.SMTPRecipientsRefused({})

            with self.assertRaises(ProviderError):
                SmtpMailer(self.config()).send(Mail("ana@example.com", "Hi", "body"))

    def test_an_unreachable_server_is_a_provider_error(self):
        with mock.patch(
            "app.core.shared.mail.smtplib.SMTP", side_effect=OSError("refused")
        ):
            with self.assertRaises(ProviderError):
                SmtpMailer(self.config()).send(Mail("ana@example.com", "Hi", "body"))
