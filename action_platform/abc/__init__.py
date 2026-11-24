"""Action Platform abstract base classes."""

from action_platform.core.events import EVENT_KINDS, Event
from action_platform.core.service_access.provider import AccessProvider

from .changelog_renderer import ChangelogRenderer
from .ci_runner import CIRunner
from .deploy_target import DeployTarget
from .plugin import Connection, Option, Plugin, Surface
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
    "EVENT_KINDS",
    "AccessProvider",
    "CIRunner",
    "ChangelogRenderer",
    "Connection",
    "DeployTarget",
    "Event",
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
