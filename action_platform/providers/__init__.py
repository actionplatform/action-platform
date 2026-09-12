"""Action Platform built-in providers.

- `source`: GitHub, GitLab, Bitbucket, generic git — repositories, releases, pull requests.
- deploy targets and CI runners are discovered through entry points (see core.module).
"""

from action_platform.providers.source.github import SourceGithub

__all__ = ["SourceGithub"]
