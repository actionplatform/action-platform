"""Templates: the matrix the API answers (official plus the organization's sources), the published index, git-flow rules."""

from app.services.templates.published import TemplatesIndex, index, plugins_index
from app.services.templates.service import CatalogService
from app.services.templates.sources import OFFICIAL_REF, MatrixView, TemplateRepos

__all__ = [
    "OFFICIAL_REF",
    "CatalogService",
    "MatrixView",
    "TemplateRepos",
    "TemplatesIndex",
    "index",
    "plugins_index",
]
