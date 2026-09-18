"""Action Platform built-in providers.

- `source`: GitHub, GitLab, Bitbucket, generic git — repositories, releases, pull requests.
- `ci`: GitHub Actions, Jenkins — the runs of an app's job.
- deploy targets and CI runners are discovered through entry points (see core.module).
"""

from action_platform.providers.source.github import SourceGithub

__all__ = ["SourceGithub"]
