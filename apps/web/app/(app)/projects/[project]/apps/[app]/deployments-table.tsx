import { Cloud, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/panel";
import type { DeployResult } from "@/lib/api";
import type { JobRow } from "@/lib/v1";

function formatDate(d: string | null | undefined): string {
  if (!d) return "—";
  const t = new Date(d);
  return Number.isNaN(t.getTime()) ? d : t.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function outcome(job: JobRow): { tone: "ok" | "bad" | "neutral" | "inverse"; label: string } {
  if (job.status === "queued") return { tone: "neutral", label: "Queued" };
  if (job.status === "running") return { tone: "inverse", label: "Running" };
  if (job.status === "failed") return { tone: "bad", label: "Failed" };
  const rows = Array.isArray(job.result) ? (job.result as DeployResult[]) : [];
  if (rows.some((r) => !r.ok)) return { tone: "bad", label: "Failed" };
  return { tone: "ok", label: job.dry_run ? "Preflight ok" : "Deployed" };
}

export function DeploymentsTable({ jobs }: { jobs: JobRow[] }) {
  return (
    <Panel>
      <PanelHeader title="All deployments" aside={<span className="text-[13px] text-secondary">{jobs.length} {jobs.length === 1 ? "run" : "runs"} · last 20</span>} />
      {jobs.length === 0 ? (
        <div className="flex flex-col items-center px-4 py-10 text-center">
          <Cloud className="size-5 text-secondary" strokeWidth={1.5} />
          <div className="mt-3 text-sm font-medium">No deployments yet</div>
          <div className="text-[13px] text-secondary">Run a preflight or deploy above; every run lands here.</div>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto"><table className="hidden w-full min-w-[640px] text-sm md:table">
            <thead><tr className="text-left text-xs text-muted-foreground"><th className="px-4 py-2 font-medium">Result</th><th className="py-2 font-medium">Stage</th><th className="py-2 font-medium">Kind</th><th className="py-2 font-medium">Version</th><th className="py-2 font-medium">URL</th><th className="py-2 font-medium">By</th><th className="py-2 pr-4 font-medium">When</th></tr></thead>
            <tbody className="divide-y divide-border-subtle border-t border-border-subtle">
              {jobs.map((job) => {
                const rows = Array.isArray(job.result) ? (job.result as DeployResult[]) : [];
                const first = rows[0];
                const o = outcome(job);
                const error = job.error ?? rows.find((r) => r.error)?.error ?? null;
                return (
                  <tr key={job.id} className="align-top">
                    <td className="px-4 py-2.5">
                      <Badge tone={o.tone}>{o.label}</Badge>
                      {error && <div className="mt-1 max-w-md break-words font-mono text-xs text-secondary">{error}</div>}
                    </td>
                    <td className="whitespace-nowrap py-2.5 pr-4 font-mono">{job.stage ?? "dev"}</td>
                    <td className="whitespace-nowrap py-2.5 pr-4 text-secondary">{job.dry_run ? "Preflight" : "Deploy"}</td>
                    <td className="whitespace-nowrap py-2.5 pr-4 font-mono">{first?.version || "—"}</td>
                    <td className="max-w-0 truncate py-2.5 pr-4">{first?.url ? <a href={first.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-secondary hover:text-foreground">{first.url} <ExternalLink className="size-3 shrink-0" strokeWidth={1.75} /></a> : <span className="text-muted-foreground">—</span>}</td>
                    <td className="whitespace-nowrap py-2.5 pr-4 text-secondary">{job.by ?? "—"}</td>
                    <td className="whitespace-nowrap py-2.5 pr-4 text-secondary">{formatDate(job.finished_at ?? job.created_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table></div>
          <ul className="divide-y divide-border-subtle border-t border-border-subtle md:hidden">
            {jobs.map((job) => {
              const rows = Array.isArray(job.result) ? (job.result as DeployResult[]) : [];
              const o = outcome(job);
              return (
                <li key={job.id} className="space-y-1 px-4 py-3 text-sm">
                  <div className="flex items-center gap-2"><Badge tone={o.tone}>{o.label}</Badge><span className="font-mono">{job.stage ?? "dev"}</span><span className="text-secondary">{job.dry_run ? "preflight" : "deploy"}</span></div>
                  <div className="text-xs text-secondary">{rows[0]?.version ? `${rows[0].version} · ` : ""}{job.by ?? "—"} · {formatDate(job.finished_at ?? job.created_at)}</div>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </Panel>
  );
}
