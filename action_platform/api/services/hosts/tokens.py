"""What every provider's token endpoint answers, read into one tuple."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from action_platform.api.services.shared.clock import now
from action_platform.core.exception import ProviderError


class TokenResponse:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data

    def read(self) -> tuple[str, Optional[str], Optional[datetime]]:
        access = self.data.get("access_token")

        if not isinstance(access, str) or not access:
            raise ProviderError(
                str(
                    self.data.get("error_description")
                    or self.data.get("error")
                    or "no access token in the provider's response"
                )
            )

        expires_in = self.data.get("expires_in")
        refresh = self.data.get("refresh_token")

        return (
            access,
            refresh if isinstance(refresh, str) else None,
            now() + timedelta(seconds=int(expires_in))
            if isinstance(expires_in, (int, float))
            else None,
        )
