from __future__ import annotations

import ipaddress
import json
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from action_platform.core import destination
from action_platform.core.destination import (
    DestinationError,
    NetworkPolicy,
    guard_networks,
)
from action_platform.core.service_access import AccessError, Http
from action_platform.providers.source import rest


class Server:
    def __init__(self) -> None:
        self.seen: list[tuple[str, dict[str, str]]] = []
        self.routes: dict[str, tuple[int, dict[str, str], bytes]] = {}
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                server.seen.append(
                    (self.path, {k.lower(): v for k, v in self.headers.items()})
                )
                status, headers, body = server.routes.get(self.path, (404, {}, b"{}"))
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def json(self, path: str, data, **headers: str) -> None:
        self.routes[path] = (200, headers, json.dumps(data).encode())

    def redirect(self, path: str, location: str) -> None:
        self.routes[path] = (302, {"location": location}, b"")


class ServersCase(unittest.TestCase):
    def setUp(self):
        self.a = Server()
        self.b = Server()
        self.addCleanup(self.a.close)
        self.addCleanup(self.b.close)
        guard_networks(NetworkPolicy())
        self.addCleanup(guard_networks, NetworkPolicy())

    def headers_at(self, server: Server, path: str) -> dict[str, str]:
        return next(h for p, h in server.seen if p == path)


class RedirectTest(ServersCase):
    def test_a_redirect_on_the_origin_keeps_the_credentials(self):
        self.a.redirect("/old", f"{self.a.url}/new")
        self.a.json("/new", {"ok": True})

        rest.call("GET", f"{self.a.url}/old", {"authorization": "Bearer t"})

        self.assertEqual(self.headers_at(self.a, "/new")["authorization"], "Bearer t")

    def test_a_redirect_off_the_origin_drops_every_credential_header(self):
        self.a.redirect("/old", f"{self.b.url}/landing")
        self.b.json("/landing", {"ok": True})

        rest.call(
            "GET",
            f"{self.a.url}/old",
            {"authorization": "Bearer t", "private-token": "glpat", "x-api-key": "k"},
        )
        seen = self.headers_at(self.b, "/landing")

        self.assertNotIn("authorization", seen)
        self.assertNotIn("private-token", seen)
        self.assertNotIn("x-api-key", seen)
        self.assertEqual(seen["user-agent"], "action-platform")

    def test_the_service_client_strips_too(self):
        http = Http("svc", self.a.url, {"authorization": "Bearer s"})
        self.a.redirect("/svc", f"{self.b.url}/svc")
        self.b.json("/svc", [])

        http.call("GET", "/svc")

        self.assertNotIn("authorization", self.headers_at(self.b, "/svc"))

    def test_a_redirect_into_a_refused_network_fails(self):
        guard_networks(
            NetworkPolicy.from_env({"AP_ALLOW_PRIVATE_NETWORKS": "127.0.0.1/32"})
        )
        self.a.redirect("/old", "http://169.254.169.254/latest/meta-data/")

        with self.assertRaises(DestinationError):
            rest.call("GET", f"{self.a.url}/old", {"authorization": "Bearer t"})


class PaginationTest(ServersCase):
    def test_a_next_link_off_the_origin_is_refused(self):
        self.a.json("/rows", {"values": [1], "next": f"{self.b.url}/rows?page=2"})

        with self.assertRaises(DestinationError) as raised:
            rest.get_values(f"{self.a.url}/rows", {"authorization": "Bearer t"})

        self.assertIn(self.b.url, str(raised.exception))
        self.assertEqual(self.b.seen, [])

    def test_a_next_link_on_the_origin_is_followed(self):
        self.a.json("/rows", {"values": [1], "next": f"{self.a.url}/rows2"})
        self.a.json("/rows2", {"values": [2]})

        self.assertEqual(
            rest.get_values(f"{self.a.url}/rows", {"authorization": "Bearer t"}),
            [1, 2],
        )

    def test_a_link_header_off_the_origin_is_refused(self):
        http = Http("svc", self.a.url, {"authorization": "Bearer s"})
        self.a.json("/items", [1], link=f'<{self.b.url}/items?c=2>; rel="next"')

        with self.assertRaises(AccessError):
            list(http.pages("/items"))

        self.assertEqual(self.b.seen, [])

    def test_an_absolute_path_off_the_base_is_refused(self):
        http = Http("svc", self.a.url, {"authorization": "Bearer s"})

        with self.assertRaises(AccessError):
            http.call("GET", f"{self.b.url}/anything")

        self.assertEqual(self.b.seen, [])


class NetworkPolicyTest(unittest.TestCase):
    def setUp(self):
        self.addCleanup(guard_networks, NetworkPolicy())

    def test_internal_addresses_are_refused_by_default(self):
        policy = NetworkPolicy.from_env({})

        for url in (
            "http://127.0.0.1:8080/x",
            "http://localhost/x",
            "http://169.254.169.254/latest/meta-data/",
            "https://10.0.0.5/x",
            "https://172.16.3.4/x",
            "https://192.168.1.10/x",
            "https://[::1]/x",
            "https://[fd00::1]/x",
            "https://[::ffff:127.0.0.1]/x",
            "https://0.0.0.0/x",
            "https://100.64.0.1/x",
        ):
            with self.subTest(url=url), self.assertRaises(DestinationError):
                policy.check(url)

        policy.check("https://93.184.215.14/x")

    def test_the_operator_opts_in(self):
        private = NetworkPolicy.from_env({"AP_ALLOW_PRIVATE_NETWORKS": "1"})
        private.check("https://10.0.0.5/x")
        private.check("http://127.0.0.1:8080/x")

        with self.assertRaises(DestinationError):
            private.check("http://169.254.169.254/latest/meta-data/")

        narrow = NetworkPolicy.from_env(
            {"AP_ALLOW_PRIVATE_NETWORKS": "10.1.0.0/16, ci.internal, 169.254.10.0/24"}
        )
        narrow.check("https://10.1.2.3/x")
        narrow.check("https://ci.internal/x")
        narrow.check("http://169.254.10.1/x")

        for url in ("https://10.2.0.1/x", "http://169.254.169.254/x"):
            with self.subTest(url=url), self.assertRaises(DestinationError):
                narrow.check(url)

        self.assertEqual(narrow.networks[0], ipaddress.ip_network("10.1.0.0/16"))

    def test_the_library_alone_does_not_enforce(self):
        NetworkPolicy().check("http://127.0.0.1/x")

    def test_urlopen_refuses_before_connecting(self):
        guard_networks(NetworkPolicy.from_env({}))
        request = urllib.request.Request(
            "http://10.255.255.1/x", headers={"authorization": "Bearer t"}
        )

        with self.assertRaises(DestinationError):
            destination.urlopen(request, timeout=1)
