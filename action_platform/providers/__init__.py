"""Action Platform built-in providers.

- `source`: GitHub, GitLab, Bitbucket, generic git — repositories, releases, pull requests.
- `ci`: GitHub Actions, Jenkins — the runs of an app's job.
- `deploy`: PyPI, npm, container registries — targets someone else publishes to, verified by the platform.
- `access`: GitHub — members, teams and repository permissions of an organization, for service access.
- deploy targets and CI runners are discovered through entry points (see core.module).
"""

from action_platform.providers.source.github import SourceGithub

__all__ = ["SourceGithub"]
