"""Changelog rendering tests."""

from pathlib import Path

from action_platform.core.release import changelog


def test_render_buckets():
    out = changelog.render(
        "0.2.0",
        [
            "feat(api): new provider",
            "fix: crash on empty tag",
            "ci: release v0.1.9",
            "feat!: drop python 3.9",
            "not a conventional commit",
        ],
    )
    assert "## v0.2.0" in out
    assert "### Breaking Changes" in out and "- drop python 3.9" in out
    assert "### Features" in out and "- **api:** new provider" in out
    assert "### Bug Fixes" in out and "- crash on empty tag" in out
    assert "### CI" in out
    assert "not a conventional" not in out


def test_render_empty():
    out = changelog.render("0.1.0", [])
    assert out.startswith("## v0.1.0")


def test_prepend_accumulates(tmp_path: Path):
    path = tmp_path / "CHANGELOG.md"
    changelog.prepend(path, changelog.render("0.1.0", ["feat: first"]))
    changelog.prepend(path, changelog.render("0.2.0", ["fix: second"]))
    text = path.read_text()

    assert text.startswith("# Changelog\n")
    assert text.count("# Changelog") == 1
    assert text.index("## v0.2.0") < text.index("## v0.1.0")
    assert "- second" in text and "- first" in text
