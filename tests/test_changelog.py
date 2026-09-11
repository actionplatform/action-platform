"""Changelog rendering tests."""

from devtool.core import changelog


def test_render_buckets():
    out = changelog.render(
        "0.2.0",
        [
            "⚙️ FEATURE: new provider",
            "🪲 BUG: crash on empty tag",
            "⬆️ CI/CD: release v0.1.9",
            "⚠️ SECURITY: patch token leak",
        ],
    )
    assert "## v0.2.0" in out
    assert "### Features" in out
    assert "- new provider" in out
    assert "### Bug Fixes" in out
    assert "- crash on empty tag" in out
    assert "### Security" in out
    assert "- patch token leak" in out


def test_render_ignores_unparseable():
    out = changelog.render("0.1.0", ["garbage line"])
    assert "## v0.1.0" in out
    assert "- garbage line" not in out
