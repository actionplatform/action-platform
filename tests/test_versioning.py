"""Versioning tests."""

import pytest

from devtool.core import versioning
from devtool.core.exception import DevtoolError


def test_bump_patch():
    assert versioning.bump("1.2.3", "patch") == "1.2.4"


def test_bump_minor():
    assert versioning.bump("1.2.3", "minor") == "1.3.0"


def test_bump_major():
    assert versioning.bump("1.2.3", "major") == "2.0.0"


def test_bump_explicit():
    assert versioning.bump("1.2.3", "2.5.0") == "2.5.0"


def test_bump_invalid():
    with pytest.raises(DevtoolError):
        versioning.bump("not-a-version", "patch")
