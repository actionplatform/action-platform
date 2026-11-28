"""Action Platform abstract base classes."""

from action_platform.core.service_access.provider import AccessProvider

from .branch_protection import BranchProtection
from .changelog_renderer import ChangelogRenderer
from .ci_runner import CIRunner
from .deploy_target import DeployTarget
from .plugin import Connection, Option, Plugin, Surface
from .release_strategy import ReleaseStrategy
from .source_host import (
    ListsPullRequests,
    PublishesReleases,
    ReadsRepository,
    SourceHost,
    SupportsRepoCreation,
    SupportsRepoDeletion,
)
from .target_operations import TargetOperations
from .template_store import TemplateStore
from .working_copy import WorkingCopy

__all__ = [
    "AccessProvider",
    "BranchProtection",
    "CIRunner",
    "ChangelogRenderer",
    "Connection",
    "DeployTarget",
    "ListsPullRequests",
    "Option",
    "Plugin",
    "PublishesReleases",
    "ReadsRepository",
    "ReleaseStrategy",
    "SourceHost",
    "SupportsRepoCreation",
    "SupportsRepoDeletion",
    "Surface",
    "TargetOperations",
    "TemplateStore",
    "WorkingCopy",
]
