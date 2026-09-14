"""Import a GitHub organization: repositories become projects with one app each, teams become teams, people become members or invitations."""

from action_platform.api.services.github_import.client import GithubDirectory
from action_platform.api.services.github_import.importer import GithubImport

__all__ = ["GithubDirectory", "GithubImport"]
