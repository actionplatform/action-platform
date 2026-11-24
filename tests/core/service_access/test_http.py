"""action_platform.core.service_access.http — plain-text reads and error messages without HTML."""

from __future__ import annotations

import io
import unittest
import urllib.error
from email.message import Message
from unittest import mock

from action_platform.core.service_access import Http
from action_platform.core.service_access.provider import AccessError

PAGE = (
    "<html><head><meta charset='utf-8'><title>Error 404 Not Found</title></head>"
    "<body><h2>HTTP ERROR 404</h2><p>Problem accessing /job/x/api/json.</p></body></html>"
)


class Body(io.BytesIO):
    def __init__(self, raw: bytes, charset: str | None = None) -> None:
        super().__init__(raw)
        self.status = 200
        self.headers = Message()

        if charset:
            self.headers["content-type"] = f"text/plain; charset={charset}"


def refused(code: int, body: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://ci.example/x", code, "error", Message(), io.BytesIO(body.encode())
    )


class TextTest(unittest.TestCase):
    def setUp(self):
        self.http = Http("jenkins", "https://ci.example", {"authorization": "Basic x"})
        self.log = "".join(f"line {i}\n" for i in range(1, 5001))

    def opened(self, answer):
        return mock.patch(
            "action_platform.core.destination.urlopen", side_effect=[answer]
        )

    def test_a_long_body_comes_back_whole(self):
        with self.opened(Body(self.log.encode())):
            text = self.http.text("job/x/1/consoleText")

        self.assertEqual(text, self.log)

    def test_tail_lines_keeps_only_the_end(self):
        with self.opened(Body(self.log.encode())):
            text = self.http.text("job/x/1/consoleText", tail_lines=2)

        self.assertEqual(text, "line 4999\nline 5000\n")

    def test_the_charset_of_the_answer_is_used(self):
        with self.opened(Body("ação\n".encode("latin-1"), "iso-8859-1")):
            self.assertEqual(self.http.text("log"), "ação\n")

    def test_an_error_names_the_call_and_never_the_page(self):
        with self.opened(refused(404, PAGE)):
            with self.assertRaises(AccessError) as caught:
                self.http.text("job/x/1/consoleText")

        message = str(caught.exception)
        self.assertEqual(
            message,
            "jenkins: GET /job/x/1/consoleText answered 404: an HTML page titled 'Error 404 Not Found'",
        )


class ErrorDetailTest(unittest.TestCase):
    def setUp(self):
        self.http = Http("jenkins", "https://ci.example", {})

    def failing(self, body: str) -> str:
        with mock.patch(
            "action_platform.core.destination.urlopen", side_effect=[refused(404, body)]
        ):
            with self.assertRaises(AccessError) as caught:
                self.http.call("GET", "job/x/api/json")

        return str(caught.exception)

    def test_an_html_error_page_is_named_by_its_title(self):
        message = self.failing(PAGE)

        self.assertTrue(
            message.endswith("answered 404: an HTML page titled 'Error 404 Not Found'")
        )
        self.assertNotIn("<", message)

    def test_an_html_page_without_a_title_is_just_an_html_page(self):
        message = self.failing("\n<!DOCTYPE html>\n<body>gone</body>")

        self.assertTrue(message.endswith("answered 404: an HTML page"))

    def test_json_and_plain_text_details_stay(self):
        self.assertTrue(
            self.failing('{"message": "no such job"}').endswith(": no such job")
        )
        self.assertTrue(self.failing("no such job").endswith(": no such job"))
