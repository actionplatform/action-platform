"""The instance's health: what anyone may probe, and what an owner sees."""

from typing import Optional

from pydantic import BaseModel

from app.schemas.common import UtcDateTime


class Health(BaseModel):
    status: str
    database: bool
    migrations: bool
    workers: dict[str, bool]


class WorkerRow(BaseModel):
    name: str
    kinds: list[str]
    started_at: UtcDateTime
    last_seen: UtcDateTime
    alive: bool


class QueueRow(BaseModel):
    kind: str
    group: str
    queued: int
    running: int
    oldest_queued_seconds: Optional[int] = None
    worker_running: bool


class SmtpOut(BaseModel):
    configured: bool
    host: Optional[str] = None
    port: Optional[int] = None
    security: Optional[str] = None
    sender: Optional[str] = None


class GoogleOut(BaseModel):
    configured: bool
    redirect_uri: str


class OAuthAppState(BaseModel):
    provider: str
    configured: bool


class Integrations(BaseModel):
    smtp: SmtpOut
    google: GoogleOut
    sentry_api: bool
    oauth_apps: list[OAuthAppState]


class InstanceHealthOut(Health):
    version: str
    api: str
    workers_seen: list[WorkerRow]
    queue: list[QueueRow]
    integrations: Integrations


class TestEmailOut(BaseModel):
    sent: bool
    to: str
    error: Optional[str] = None
