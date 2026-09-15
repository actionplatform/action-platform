"""The templates catalog: the matrix the API answers, and which repository a request reads templates from."""

from app.services.catalog.published import TemplatesIndex, index
from app.services.catalog.service import (
    OFFICIAL_REF,
    CatalogService,
    MatrixView,
    TemplateRepos,
)

__all__ = [
    "OFFICIAL_REF",
    "CatalogService",
    "MatrixView",
    "TemplateRepos",
    "TemplatesIndex",
    "index",
]
