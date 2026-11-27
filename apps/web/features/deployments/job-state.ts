import type { DeployResult } from "@/lib/api";
import type { JobRow } from "@/lib/v1";

export type Status = { tone: "danger" | "warning" | "success" | "neutral"; label: string };

export function rowsOf(job: JobRow): DeployResult[] {
  return Array.isArray(job.result) ? (job.result as DeployResult[]) : [];
}

export function statusOf(job: JobRow): Status {
  if (job.status === "queued" && job.no_worker) return { tone: "warning", label: "No worker running" };
  if (job.status === "queued") return { tone: "neutral", label: "Queued" };
  if (job.status === "running") return { tone: "warning", label: "Running" };
  if (job.status === "failed" || rowsOf(job).some((r) => !r.ok)) return { tone: "danger", label: "Failed" };
  return { tone: "success", label: "Successful" };
}

export function errorOf(job: JobRow): string | null {
  return job.error ?? rowsOf(job).find((r) => r.error)?.error ?? null;
}

export function versionOf(job: JobRow): string | null {
  return rowsOf(job)[0]?.version || job.version || null;
}

export function typeOf(job: JobRow): string {
  return job.kind === "destroy" ? "Tear down" : job.dry_run ? "Preflight" : "Deploy";
}

export function canRedeploy(job: JobRow, canDeploy: boolean): boolean {
  return canDeploy && job.kind !== "destroy" && !!versionOf(job);
}

export function when(d: string | null | undefined): string {
  if (!d) return "—";
  const t = new Date(d);
  return Number.isNaN(t.getTime()) ? d : t.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function elapsed(job: JobRow, now: number): string {
  const from = new Date(job.started_at ?? job.created_at).getTime();
  const to = job.finished_at ? new Date(job.finished_at).getTime() : job.status === "running" ? now : null;
  if (!to || Number.isNaN(from)) return "—";
  const s = Math.max(0, Math.round((to - from) / 1000));
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, "0")}s`;
}

export function deploymentHref(base: string, id: string): string {
  return `${base}/deployments/${encodeURIComponent(id)}`;
}

export function releaseTag(version: string): string {
  return /^v\d/.test(version) || version.includes("/") ? version : `v${version}`;
}
