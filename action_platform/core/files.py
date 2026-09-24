"""The files the platform keeps in a project: fixed names, not configuration."""

from pathlib import Path

CONFIG_FILE = "platform.toml"
LAST_VERSION_FILE = "LAST_VERSION"
CHANGELOG_FILE = "CHANGELOG.md"
HOOKS_DIR = Path(".action-platform/hooks")
