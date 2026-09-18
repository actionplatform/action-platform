import type { Schemas } from "./api";

type CiHostRow = Schemas["CiHostRow"];
type CiRunRow = Schemas["CiRunRow"];
type CiRunsRow = Schemas["CiRuns"];

export const CI_HOST_KINDS = [
  { id: "jenkins", label: "Jenkins", baseUrlHint: "The Jenkins root, e.g. https://ci.example.com", tokenLabel: "API token", tokenHint: "Jenkins → your user → Security → API Token.", needsUsername: true, jobHint: "The path in the job URL: team/app, or team/app/main for a multibranch branch." },
] as const;

export type CiHostKind = (typeof CI_HOST_KINDS)[number]["id"];

export const CI_LABELS: Record<string, string> = { jenkins: "Jenkins", github_actions: "GitHub Actions", gitlab_ci: "GitLab CI", bitbucket_pipelines: "Bitbucket Pipelines", none: "None" };

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
