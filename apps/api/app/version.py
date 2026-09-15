"""The HTTP API. `api_version()` is the api component's own version, released separately from the library."""

from pathlib import Path

from action_platform import __version__

_LAST_VERSION = Path(__file__).with_name("LAST_VERSION")


def api_version() -> str:
    try:
        return _LAST_VERSION.read_text().strip() or __version__
    except OSError:
        return __version__
