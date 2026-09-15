"""What every import step shares: the context of the platform organization and the host directory it reads from."""

from action_platform_api.core.abc import HostDirectory
from action_platform_api.services.organization_import.context import ImportContext


class ImportStep:
    def __init__(self, ctx: ImportContext, host: HostDirectory) -> None:
        self.ctx = ctx
        self.host = host

    @property
    def summary(self):
        return self.ctx.summary

    @property
    def writes(self):
        return self.ctx.writes

    @property
    def organization_id(self) -> str:
        return self.ctx.organization_id
