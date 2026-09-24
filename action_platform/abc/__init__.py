"""Action Platform abstract base classes."""

from .changelog_renderer import ChangelogRenderer
from .ci_runner import CIRunner
from .deploy_target import DeployTarget
from .plugin import Option, Plugin, Surface
from .release_strategy import ReleaseStrategy
from .source_host import (
    ListsPullRequests,
    PublishesReleases,
    SourceHost,
    SupportsRepoCreation,
    SupportsRepoDeletion,
)
from .template_store import TemplateStore
from .working_copy import WorkingCopy

__all__ = [
    "CIRunner",
    "ChangelogRenderer",
    "DeployTarget",
    "ListsPullRequests",
    "Option",
    "Plugin",
    "PublishesReleases",
    "ReleaseStrategy",
    "SourceHost",
    "SupportsRepoCreation",
    "SupportsRepoDeletion",
    "Surface",
    "TemplateStore",
    "WorkingCopy",
]
