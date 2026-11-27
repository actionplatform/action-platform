"""CI servers and the runs of an app."""

from typing import Optional

from pydantic import BaseModel

from app.schemas.common import UtcDateTime


class CiHostRow(BaseModel):
    id: str
    kind: str
    name: str
    base_url: str
    username: Optional[str] = None
    created_at: UtcDateTime


class AddCiHostRequest(BaseModel):
    kind: str
    name: Optional[str] = ""
    base_url: str
    token: str
    username: Optional[str] = ""


class CiLink(BaseModel):
    kind: str
    ci_host_id: Optional[str] = None
    job: str = ""


class CiLinkRequest(BaseModel):
    ci_host_id: Optional[str] = None
    job: str = ""


class CiRunRow(BaseModel):
    id: str
    source: str
    number: int
    status: str
    name: Optional[str] = None
    url: Optional[str] = None
    branch: Optional[str] = None
    sha: Optional[str] = None
    trigger: Optional[str] = None
    started_at: Optional[UtcDateTime] = None
    duration_ms: Optional[int] = None
    synced_at: UtcDateTime


class CiRuns(BaseModel):
    link: CiLink
    runs: list[CiRunRow]
    error: Optional[str] = None
    total: int = 0
    page: int = 1
    per: int = 10


class CiStartRequest(BaseModel):
    ref: str


class CiStarted(BaseModel):
    id: str
    url: Optional[str] = None
    ref: str


class CiJob(BaseModel):
    name: str
    kind: str
    label: str


class CiJobError(BaseModel):
    job: str
    error: str


class CiPipelineRun(BaseModel):
    job: str
    number: int
    status: str
    name: Optional[str] = None
    url: Optional[str] = None
    branch: Optional[str] = None
    sha: Optional[str] = None
    trigger: Optional[str] = None
    started_at: Optional[UtcDateTime] = None
    duration_ms: Optional[int] = None


class CiPipelines(BaseModel):
    kind: str
    jobs: list[CiJob]
    runs: list[CiPipelineRun]
    errors: list[CiJobError] = []


class CiStage(BaseModel):
    id: str
    name: str
    status: str
    started_at: Optional[UtcDateTime] = None
    duration_ms: Optional[int] = None
    parent_id: Optional[str] = None


class CiChange(BaseModel):
    sha: str
    author: Optional[str] = None
    message: str = ""


class CiPendingInput(BaseModel):
    id: str
    message: str


class CiSupports(BaseModel):
    log: bool = False
    tests: bool = False
    artifacts: bool = False


class CiRunDetail(BaseModel):
    run: CiPipelineRun
    job: CiJob
    parameters: dict[str, str] = {}
    causes: list[str] = []
    changes: list[CiChange] = []
    stages: Optional[list[CiStage]] = None
    pending_inputs: Optional[list[CiPendingInput]] = None
    waiting: Optional[str] = None
    supports: CiSupports


class CiLogChunk(BaseModel):
    text: str
    next_start: int
    more: bool
    truncated: bool = False


class CiTestFailure(BaseModel):
    name: str
    class_name: str = ""
    message: str = ""
    stack: str = ""


class CiTestReport(BaseModel):
    total: int
    passed: int
    failed: int
    skipped: int
    failures: list[CiTestFailure]


class CiTests(BaseModel):
    report: Optional[CiTestReport] = None


class CiArtifact(BaseModel):
    path: str
    size: Optional[int] = None


class CiArtifacts(BaseModel):
    artifacts: list[CiArtifact]


class CiAppRef(BaseModel):
    project_id: str
    app_id: str
    name: str
    job: str


class CiQueueRow(BaseModel):
    since: Optional[UtcDateTime] = None
    why: Optional[str] = None
    app: Optional[CiAppRef] = None


class CiExecutorRow(BaseModel):
    node: str
    busy: bool
    number: Optional[int] = None
    app: Optional[CiAppRef] = None


class CiHostActivity(BaseModel):
    id: str
    name: str
    kind: str
    queue: Optional[list[CiQueueRow]] = None
    executors: Optional[list[CiExecutorRow]] = None
    error: Optional[str] = None


class CiActivity(BaseModel):
    hosts: list[CiHostActivity]
