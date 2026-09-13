"""Versioning tests."""

import pytest

from action_platform.core.release import versioning
from action_platform.core.exception import ActionPlatformError


def test_bump_patch():
    assert versioning.bump("1.2.3", "patch") == "1.2.4"


def test_bump_minor():
    assert versioning.bump("1.2.3", "minor") == "1.3.0"


def test_bump_major():
    assert versioning.bump("1.2.3", "major") == "2.0.0"


def test_bump_explicit():
    assert versioning.bump("1.2.3", "2.5.0") == "2.5.0"


def test_bump_invalid():
    with pytest.raises(ActionPlatformError):
        versioning.bump("not-a-version", "patch")


def test_sync_files(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "0.1.0"\n\n[tool.poetry]\nversion = "0.1.0"\n'
    )
    (tmp_path / "package.json").write_text(
        '{\n  "name": "x",\n  "version": "0.1.0"\n}\n'
    )
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text('__version__ = "0.1.0"\n')

    touched = versioning.sync_files(tmp_path, "0.2.0")

    assert touched == ["pyproject.toml", "package.json", "pkg/__init__.py"]
    assert (tmp_path / "pyproject.toml").read_text().count('version = "0.2.0"') == 2
    assert '"version": "0.2.0"' in (tmp_path / "package.json").read_text()
    assert '__version__ = "0.2.0"' in (tmp_path / "pkg" / "__init__.py").read_text()
    assert versioning.sync_files(tmp_path, "0.2.0") == []


def test_strip_pre_and_next_rc():
    assert versioning.strip_pre("0.3.2-rc.1") == "0.3.2"
    assert versioning.next_rc("0.3.2", []) == "0.3.2-rc.1"
    assert (
        versioning.next_rc("0.3.2", ["v0.3.2-rc.1", "v0.3.2-rc.2", "v0.3.1"])
        == "0.3.2-rc.3"
    )


def test_sync_files_updates_version_constants(tmp_path):
    from pathlib import Path

    from action_platform.core.release import versioning

    files = {
        "mylib.go": 'package mylib\n\nconst Version = "0.1.0"\n',
        "internal/app/app.go": 'package app\n\nconst Version = "0.1.0"\n',
        "manifest.json": '{\n  "name": "x",\n  "version": "0.1.0"\n}\n',
        "pom.xml": "<project>\n  <groupId>g</groupId>\n  <version>0.1.0</version>\n  <dependencies>\n    <dependency>\n      <version>5.0.0</version>\n    </dependency>\n  </dependencies>\n</project>\n",
        "src/lib.rs": 'pub const VERSION: &str = "0.1.0";\n',
        "src/index.ts": 'export const VERSION = "0.1.0";\n',
        "src/Version.php": "<?php\nfinal class Version\n{\n    public const VERSION = '0.1.0';\n}\n",
        "src/main/java/com/acme/Version.java": 'public final class Version {\n    public static final String VERSION = "0.1.0";\n}\n',
    }
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    touched = versioning.sync_files(Path(tmp_path), "0.2.0")

    assert set(touched) == set(files)
    for rel in files:
        assert "0.2.0" in (tmp_path / rel).read_text()
        assert "0.1.0" not in (tmp_path / rel).read_text()
    assert "<version>5.0.0</version>" in (tmp_path / "pom.xml").read_text()
