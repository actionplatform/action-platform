"""The probe every provider reads an access check with; the report it answers in lives on the HostProvider contract."""

from __future__ import annotations

import re
from typing import Any

from action_platform.core.exception import ProviderError
from app.core.abc import AccessReport, Owner
from app.core.shared.http import http

__all__ = ["AccessReport", "Owner", "Probe"]


class Probe:
    """GET that answers (status, body) instead of raising, for checks that read what they can."""

    def __init__(self, headers: dict[str, str]) -> None:
        self.headers = headers

    def get(self, url: str) -> tuple[int, Any]:
        try:
            return 200, http.get_json(url, self.headers)
        except ProviderError as e:
            digits = re.match(r"(\d{3}) from", str(e))

            return (int(digits.group(1)) if digits else 0), None
