import type { Schemas } from "./api";

type CiHostRow = Schemas["CiHostRow"];
type CiRunRow = Schemas["CiRunRow"];
type CiRunsRow = Schemas["CiRuns"];

export const CI_HOST_KINDS = [
  { id: "jenkins", label: "Jenkins", baseUrlHint: "The Jenkins root, e.g. https://ci.example.com", tokenLabel: "API token", tokenHint: "Jenkins → your user → Security → API Token.", needsUsername: true, jobHint: "The path in the job URL: team/app, or team/app/main for a multibranch branch." },
] as const;

export type CiHostKind = (typeof CI_HOST_KINDS)[number]["id"];

export const CI_LABELS: Record<string, string> = { jenkins: "Jenkins", github_actions: "GitHub Actions", gitlab_ci: "GitLab CI", bitbucket_pipelines: "Bitbucket Pipelines", none: "None" };
export const EMBEDDED_CI: Record<string, string> = { github: "GitHub Actions", gitlab: "GitLab CI", bitbucket: "Bitbucket Pipelines" };

export type CiRunStatus = "queued" | "running" | "success" | "failure" | "unstable" | "aborted" | "unknown";

export type CiHost = { id: string; kind: CiHostKind; name: string; baseUrl: string; username: string | null; createdAt: Date };

export type CiRun = { id: string; source: string; number: number; status: CiRunStatus; name: string | null; url: string | null; branch: string | null; sha: string | null; trigger: string | null; startedAt: string | null; durationMs: number | null; syncedAt: string };

export type CiLink = { kind: string; ciHostId: string | null; job: string };

export type CiState = { link: CiLink; runs: CiRun[]; error: string | null; total: number; page: number; per: number };

export function ciHost(row: CiHostRow): CiHost {
  return { id: row.id, kind: row.kind as CiHostKind, name: row.name, baseUrl: row.base_url, username: row.username ?? null, createdAt: new Date(row.created_at) };
}

export function ciRun(r: CiRunRow): CiRun {
  return { id: r.id, source: r.source, number: r.number, status: r.status as CiRunStatus, name: r.name ?? null, url: r.url ?? null, branch: r.branch ?? null, sha: r.sha ?? null, trigger: r.trigger ?? null, startedAt: r.started_at ?? null, durationMs: r.duration_ms ?? null, syncedAt: r.synced_at };
}

export function ciState(row: CiRunsRow): CiState {
  return { link: { kind: row.link.kind, ciHostId: row.link.ci_host_id ?? null, job: row.link.job ?? "" }, runs: row.runs.map(ciRun), error: row.error ?? null, total: row.total ?? row.runs.length, page: row.page ?? 1, per: row.per ?? 10 };
}

export function duration(ms: number | null): string {
  if (ms === null) return "—";
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ${s % 60}s`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}

export function runOfRelease(runs: CiRun[], release: { tag: string; version: string; sha: string | null }): CiRun | null {
  return runs.find((r) => r.branch === release.tag || (!!release.version && r.branch === release.version) || (!!release.sha && r.sha === release.sha)) ?? null;
}

export type CiJobKind = "ci" | "cd";

export type CiJob = { name: string; kind: CiJobKind; label: string };

export type PipelineRun = { job: string; number: number; status: CiRunStatus; name: string | null; url: string | null; branch: string | null; sha: string | null; trigger: string | null; startedAt: string | null; durationMs: number | null };

export type Pipelines = { kind: string; jobs: CiJob[]; runs: PipelineRun[]; errors: { job: string; error: string }[] };

export type CiStage = { id: string; name: string; status: CiRunStatus; startedAt: string | null; durationMs: number | null; parentId: string | null };

export type CiChange = { sha: string; author: string | null; message: string };

export type PipelineRunDetail = {
  run: PipelineRun;
  job: CiJob;
  parameters: Record<string, string>;
  causes: string[];
  changes: CiChange[];
  stages: CiStage[] | null;
  pendingInputs: { id: string; message: string }[] | null;
  waiting: string | null;
  supports: { log: boolean; tests: boolean; artifacts: boolean };
};

export type CiLogChunk = { text: string; nextStart: number; more: boolean; truncated: boolean };

export type CiTestReport = { total: number; passed: number; failed: number; skipped: number; failures: { name: string; className: string; message: string; stack: string }[] };

export type CiArtifact = { path: string; size: number | null };

export type CiAppRef = { projectId: string; appId: string; name: string; job: string };

export type CiHostActivity = {
  id: string;
  name: string;
  kind: string;
  queue: { since: string | null; why: string | null; app: CiAppRef | null }[] | null;
  executors: { node: string; busy: boolean; number: number | null; app: CiAppRef | null }[] | null;
  error: string | null;
};

function status(value: string): CiRunStatus {
  return (["queued", "running", "success", "failure", "unstable", "aborted"] as const).find((s) => s === value) ?? "unknown";
}

export function pipelineRun(r: Schemas["CiPipelineRun"]): PipelineRun {
  return { job: r.job, number: r.number, status: status(r.status), name: r.name ?? null, url: r.url ?? null, branch: r.branch ?? null, sha: r.sha ?? null, trigger: r.trigger ?? null, startedAt: r.started_at ?? null, durationMs: r.duration_ms ?? null };
}

function ciJob(j: Schemas["CiJob"]): CiJob {
  return { name: j.name, kind: j.kind === "cd" ? "cd" : "ci", label: j.label };
}

export function pipelines(row: Schemas["CiPipelines"]): Pipelines {
  return { kind: row.kind, jobs: row.jobs.map(ciJob), runs: row.runs.map(pipelineRun), errors: (row.errors ?? []).map((e) => ({ job: e.job, error: e.error })) };
}

export function pipelineRunDetail(row: Schemas["CiRunDetail"]): PipelineRunDetail {
  return {
    run: pipelineRun(row.run),
    job: ciJob(row.job),
    parameters: row.parameters ?? {},
    causes: row.causes ?? [],
    changes: (row.changes ?? []).map((c) => ({ sha: c.sha, author: c.author ?? null, message: c.message ?? "" })),
    stages: row.stages ? row.stages.map((s) => ({ id: s.id, name: s.name, status: status(s.status), startedAt: s.started_at ?? null, durationMs: s.duration_ms ?? null, parentId: s.parent_id ?? null })) : null,
    pendingInputs: row.pending_inputs ? row.pending_inputs.map((i) => ({ id: i.id, message: i.message })) : null,
    waiting: row.waiting ?? null,
    supports: { log: !!row.supports.log, tests: !!row.supports.tests, artifacts: !!row.supports.artifacts },
  };
}

export function logChunk(row: Schemas["CiLogChunk"]): CiLogChunk {
  return { text: row.text, nextStart: row.next_start, more: row.more, truncated: !!row.truncated };
}

export function testReport(row: Schemas["CiTests"]): CiTestReport | null {
  const r = row.report;
  if (!r) return null;
  return { total: r.total, passed: r.passed, failed: r.failed, skipped: r.skipped, failures: r.failures.map((f) => ({ name: f.name, className: f.class_name ?? "", message: f.message ?? "", stack: f.stack ?? "" })) };
}

function appRef(a: Schemas["CiAppRef"] | null | undefined): CiAppRef | null {
  return a ? { projectId: a.project_id, appId: a.app_id, name: a.name, job: a.job } : null;
}

export function ciActivity(row: Schemas["CiActivity"]): CiHostActivity[] {
  return row.hosts.map((h) => ({
    id: h.id,
    name: h.name,
    kind: h.kind,
    queue: h.queue ? h.queue.map((q) => ({ since: q.since ?? null, why: q.why ?? null, app: appRef(q.app) })) : null,
    executors: h.executors ? h.executors.map((e) => ({ node: e.node, busy: e.busy, number: e.number ?? null, app: appRef(e.app) })) : null,
    error: h.error ?? null,
  }));
}

function query(job: string, extra: Record<string, string> = {}): string {
  return new URLSearchParams({ job, ...extra }).toString();
}

export function runHref(base: string, job: string, number: number, tab?: string): string {
  return `${base}/pipelines/${number}?${query(job, tab ? { tab } : {})}`;
}

function runApi(projectId: string, appId: string, number: number): string {
  return `/api/v1/projects/${encodeURIComponent(projectId)}/apps/${encodeURIComponent(appId)}/ci/runs/${number}`;
}

export function logDownloadHref(projectId: string, appId: string, job: string, number: number): string {
  return `${runApi(projectId, appId, number)}/log/download?${query(job)}`;
}

export function artifactHref(projectId: string, appId: string, job: string, number: number, path: string): string {
  return `${runApi(projectId, appId, number)}/artifacts/download?${query(job, { path })}`;
}

export function bytes(size: number | null): string {
  if (size === null) return "—";
  if (size < 1024) return `${size} B`;
  const units = ["KB", "MB", "GB"];
  let value = size / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit++; }
  return `${value < 10 ? value.toFixed(1) : Math.round(value)} ${units[unit]}`;
}

export type CiDeployRun = { target: string; run: PipelineRun };

export function deployRuns(row: Schemas["CiDeployRuns"]): CiDeployRun[] {
  return row.runs.map((r) => ({ target: r.target, run: pipelineRun(r.run) }));
}
