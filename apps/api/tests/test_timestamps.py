"""Timestamps the API emits carry a UTC offset."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from app.schemas.common import UtcDateTime
from pydantic import BaseModel


class Row(BaseModel):
    at: UtcDateTime
    maybe: UtcDateTime | None = None


class TimestampTest(unittest.TestCase):
    def test_naive_is_utc(self):
        row = Row(at=datetime(2026, 11, 25, 15, 19, 6, 451527))

        self.assertEqual(
            row.model_dump(mode="json")["at"], "2026-11-25T15:19:06.451527Z"
        )

    def test_aware_is_converted_to_utc(self):
        zone = timezone(timedelta(hours=-3))
        row = Row(at=datetime(2026, 11, 25, 12, 0, tzinfo=zone))

        self.assertEqual(row.model_dump_json().count("15:00:00Z"), 1)

    def test_none_stays_none(self):
        row = Row(at=datetime(2026, 1, 1))

        self.assertIsNone(row.model_dump(mode="json")["maybe"])


if __name__ == "__main__":
    unittest.main()
