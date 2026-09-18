import type { Schemas } from "./api";

type DeploymentRow = Schemas["DeploymentRow"];
type TargetRow = Schemas["TargetRow"];
type DeploymentsRow = Schemas["Deployments"];

export type Executor = "platform" | "github_actions" | "jenkins" | "manual";
export type DeploymentStatus = "queued" | "running" | "success" | "failure" | "verified";

export const EXECUTOR_LABELS: Record<string, string> = { platform: "Platform", github_actions: "GitHub Actions", jenkins: "Jenkins", manual: "Manual" };
export const KIND_LABELS: Record<string, string> = { "aws/lambda": "AWS Lambda", pypi: "PyPI", npm: "npm", docker: "Container registry" };

export type Target = { name: string; kind: string; runBy: Executor; stages: string[]; workflow: string | null; job: string | null };

export type Deployment = { id: string; target: string; kind: string; stage: string | null; version: string; sha: string | null; status: DeploymentStatus; executor: Executor; jobId: string | null; ciRunId: string | null; url: string | null; actor: string | null; error: string | null; startedAt: string | null; finishedAt: string | null; verifiedAt: string | null; syncedAt: string };

export type DeploymentsState = { targets: Target[]; deployments: Deployment[]; error: string | null };

export function target(t: TargetRow): Target {
  return { name: t.name, kind: t.kind, runBy: t.run_by as Executor, stages: t.stages ?? [], workflow: t.workflow ?? null, job: t.job ?? null };
}

export function deployment(d: DeploymentRow): Deployment {
  return { id: d.id, target: d.target, kind: d.kind, stage: d.stage ?? null, version: d.version, sha: d.sha ?? null, status: d.status as DeploymentStatus, executor: d.executor as Executor, jobId: d.job_id ?? null, ciRunId: d.ci_run_id ?? null, url: d.url ?? null, actor: d.actor ?? null, error: d.error ?? null, startedAt: d.started_at ?? null, finishedAt: d.finished_at ?? null, verifiedAt: d.verified_at ?? null, syncedAt: d.synced_at };
}

export function deploymentsState(row: DeploymentsRow): DeploymentsState {
  return { targets: row.targets.map(target), deployments: row.deployments.map(deployment), error: row.error ?? null };
}

export type Live = { stage: string | null; version: string; status: DeploymentStatus; at: string | null };

export function liveOf(target: Target, rows: Deployment[]): Live[] {
  const mine = rows.filter((d) => d.target === target.name && (d.status === "success" || d.status === "verified"));
  const stages = target.stages.length ? target.stages : [null];
  return stages.map((stage) => {
    const last = mine.find((d) => (stage === null ? true : d.stage === stage));
    return last ? { stage, version: last.version, status: last.status, at: last.finishedAt ?? last.startedAt } : { stage, version: "—", status: "queued", at: null };
  });
}
