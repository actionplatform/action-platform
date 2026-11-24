from __future__ import annotations

import unittest
from unittest import mock

from action_platform.core.destination import DestinationError

try:
    from app.core.shared.http import HttpClient
except ImportError:
    HttpClient = None


@unittest.skipUnless(HttpClient, "the API is not installed")
class HttpClientTest(unittest.TestCase):
    def test_a_next_link_off_the_origin_is_refused(self):
        client = HttpClient()
        pages = {
            "https://api.bitbucket.org/2.0/repositories/ws": {
                "values": [1],
                "next": "https://evil.example.com/2.0/repositories/ws?page=2",
            }
        }

        with mock.patch.object(
            client, "get_json", side_effect=lambda url, headers: pages[url]
        ) as get:
            with self.assertRaises(DestinationError):
                client.get_values(
                    "https://api.bitbucket.org/2.0/repositories/ws",
                    {"authorization": "Bearer t"},
                )

        self.assertEqual(get.call_count, 1)

    def test_a_next_link_on_the_origin_is_followed(self):
        client = HttpClient()
        first = "https://api.bitbucket.org/2.0/repositories/ws"
        second = f"{first}?page=2"
        pages = {first: {"values": [1], "next": second}, second: {"values": [2]}}

        with mock.patch.object(
            client, "get_json", side_effect=lambda url, headers: pages[url]
        ):
            self.assertEqual(client.get_values(first, {}), [1, 2])

    def test_requests_go_through_the_destination_policy(self):
        with mock.patch(
            "action_platform.core.destination.urlopen",
            side_effect=DestinationError("refused"),
        ) as opened:
            with self.assertRaises(DestinationError):
                HttpClient().get_json("https://10.0.0.5/api", {"authorization": "x"})

        self.assertEqual(opened.call_args.args[0].full_url, "https://10.0.0.5/api")
