from __future__ import annotations

import unittest

from action_platform.core.origin import Origin, OriginError


class OriginTest(unittest.TestCase):
    def test_scheme_host_and_default_port(self):
        self.assertEqual(
            Origin.of("https://GitHub.com/acme/x.git"),
            Origin("https", "github.com", 443),
        )
        self.assertEqual(
            Origin.of("https://github.com:443/a"), Origin.of("https://github.com")
        )
        self.assertEqual(Origin.of("http://git.example.com").port, 80)
        self.assertEqual(
            Origin.of("https://git.example.com:8443/x").url,
            "https://git.example.com:8443",
        )
        self.assertEqual(Origin.of("https://[::1]:8443/").url, "https://[::1]:8443")

    def test_userinfo_does_not_change_the_host(self):
        self.assertEqual(
            Origin.of("https://github.com@evil.com/acme/x").host, "evil.com"
        )
        self.assertEqual(
            Origin.of("https://user@bitbucket.org/ws/x.git").host, "bitbucket.org"
        )

    def test_ambiguous_urls_are_refused(self):
        for url in (
            "",
            "https://user:secret@github.com/acme/x",
            "https://github.com\\@evil.com/x",
            "https://github.com /x",
            "https://github.com\n.evil.com/x",
            "https://github.com:99999/x",
            "https://github.com:abc/x",
            "ssh://git@github.com/acme/x",
            "git@github.com:acme/x.git",
            "file:///tmp/x",
            "https:///x",
        ):
            with self.subTest(url=url), self.assertRaises(OriginError):
                Origin.of(url)

        self.assertIsNone(Origin.parse("ssh://github.com/x"))
        self.assertIsNone(Origin.parse(None))

    def test_matches_only_the_same_scheme_host_and_port(self):
        origin = Origin.of("https://github.com")

        self.assertTrue(origin.matches("https://github.com/acme/x.git"))
        self.assertTrue(origin.matches("https://user@github.com:443/acme/x.git"))

        for url in (
            "http://github.com/acme/x",
            "https://github.com:8443/acme/x",
            "https://github.com.evil.com/acme/x",
            "https://evil.com/github.com/acme/x",
            "https://github.com@evil.com/acme/x",
            "https://api.github.com/x",
            "https://user:pw@github.com/x",
        ):
            with self.subTest(url=url):
                self.assertFalse(origin.matches(url))

    def test_require_names_both_origins(self):
        origin = Origin.of("https://gitlab.example.com")

        self.assertEqual(
            origin.require("https://gitlab.example.com/a/b"),
            "https://gitlab.example.com/a/b",
        )

        with self.assertRaises(OriginError) as raised:
            origin.require("https://evil.example.org/a/b")

        self.assertIn("https://evil.example.org", str(raised.exception))
        self.assertIn("https://gitlab.example.com", str(raised.exception))
