"""Where a credential may go: the scheme, host and port of an approved destination, and the check every authenticated URL passes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlsplit

DEFAULT_PORTS = {"https": 443, "http": 80}


class OriginError(ValueError):
    pass


@dataclass(frozen=True)
class Origin:
    scheme: str
    host: str
    port: int

    @classmethod
    def of(cls, url: str) -> "Origin":
        """The origin of an http(s) URL; anything ambiguous (control characters, backslashes, a password in the URL, a bad port) is refused rather than guessed."""
        if not url or any(c.isspace() or ord(c) < 32 or c == "\\" for c in url):
            raise OriginError(f"not a usable URL: {url!r}")

        parts = urlsplit(url)
        scheme = parts.scheme.lower()

        if scheme not in DEFAULT_PORTS:
            raise OriginError(f"not an http(s) URL: {url}")

        if parts.password is not None:
            raise OriginError(f"URL carries a password: {parts.hostname}")

        try:
            port = parts.port or DEFAULT_PORTS[scheme]
        except ValueError as e:
            raise OriginError(f"bad port in URL: {url}") from e

        host = (parts.hostname or "").rstrip(".")

        if not host:
            raise OriginError(f"URL has no host: {url}")

        return cls(scheme, host, port)

    @classmethod
    def parse(cls, url: Optional[str]) -> Optional["Origin"]:
        """`of`, or None when the URL is missing or unusable."""
        try:
            return cls.of(url or "")
        except OriginError:
            return None

    @property
    def url(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host

        if self.port == DEFAULT_PORTS[self.scheme]:
            return f"{self.scheme}://{host}"

        return f"{self.scheme}://{host}:{self.port}"

    def matches(self, url: Optional[str]) -> bool:
        return Origin.parse(url) == self

    def require(self, url: str) -> str:
        """`url` itself when it is on this origin; otherwise the credential must not follow it."""
        if not self.matches(url):
            raise OriginError(
                f"{_shown(url)} is outside {self.url}; credentials for {self.url} are not sent there"
            )

        return url

    def __str__(self) -> str:
        return self.url


def _shown(url: str) -> str:
    origin = Origin.parse(url)

    return origin.url if origin else repr(url)
