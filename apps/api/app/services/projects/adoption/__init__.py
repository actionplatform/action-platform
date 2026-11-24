"""Adoption: bringing a project's apps onto the platform in one run — where each stands, the plans, the install pull requests."""

from app.services.projects.adoption.install import BulkInstall, InstallOptions
from app.services.projects.adoption.service import JOB_KIND, Adoption

__all__ = ["JOB_KIND", "Adoption", "BulkInstall", "InstallOptions"]
