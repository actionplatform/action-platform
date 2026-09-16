"use client";

import { ChevronDown, Cloud, ExternalLink, MoreHorizontal, RotateCcw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Menu } from "@/components/ui/menu";
import { Panel, PanelHeader } from "@/components/ui/panel";
import type { DeployResult } from "@/lib/api";
import type { JobRow } from "@/lib/v1";
import { cn } from "@/lib/utils";
import { startDeploy } from "@/features/deployments/actions";
import { CopyButton, LogBox, summarize } from "./run-alert";

type Status = { tone: "danger" | "warning" | "success" | "neutral"; label: string };

function rowsOf(job: JobRow): DeployResult[] {
  return Array.isArray(job.result) ? (job.result as DeployResult[]) : [];
}

function statusOf(job: JobRow): Status {
  if (job.status === "queued") return { tone: "neutral", label: "Queued" };
  if (job.status === "running") return { tone: "warning", label: "Running" };
  if (job.status === "failed" || rowsOf(job).some((r) => !r.ok)) return { tone: "danger", label: "Failed" };
  return { tone: "success", label: "Successful" };
}

function errorOf(job: JobRow): string | null {
  return job.error ?? rowsOf(job).find((r) => r.error)?.error ?? null;
}

function when(d: string | null | undefined): string {
  if (!d) return "—";
  const t = new Date(d);
  return Number.isNaN(t.getTime()) ? d : t.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function duration(job: JobRow, now: number): string {
  const from = new Date(job.started_at ?? job.created_at).getTime();
  const to = job.finished_at ? new Date(job.finished_at).getTime() : job.status === "running" ? now : null;
  if (!to || Number.isNaN(from)) return "—";
  const s = Math.max(0, Math.round((to - from) / 1000));
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, "0")}s`;
}

const versionOf = (job: JobRow): string | null => rowsOf(job)[0]?.version || job.version || null;

export function DeploymentsTable({ jobs, registryId, canDeploy }: { jobs: JobRow[]; registryId: string; canDeploy: boolean }) {
  const router = useRouter();
  const [open, setOpen] = useState<string | null>(null);
  const [details, setDetails] = useState<JobRow | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [pending, start] = useTransition();
  const live = jobs.some((j) => j.status === "running" || j.status === "queued");

  useEffect(() => {
    if (!live) return;
    const timer = setInterval(() => { setNow(Date.now()); router.refresh(); }, 4000);
    return () => clearInterval(timer);
  }, [live, router]);

  const redeploy = (job: JobRow) =>
    start(async () => {
      const r = await startDeploy(registryId, job.stage ?? "dev", !!job.dry_run, job.version ?? versionOf(job) ?? "");
      if (r.ok) router.refresh();
    });

  const actions = (job: JobRow) => [
    { label: "View details", onSelect: () => setDetails(job) },
    ...(canDeploy && job.kind !== "destroy" && (job.version || versionOf(job)) ? [{ label: job.dry_run ? "Run preflight again" : "Redeploy", icon: <RotateCcw className="size-3.5" strokeWidth={1.75} />, onSelect: () => redeploy(job) }] : []),
  ];

  return (
    <Panel>
      <PanelHeader title="Deployment history" aside={<span className="text-[13px] text-secondary">{jobs.length} {jobs.length === 1 ? "run" : "runs"} · last 20</span>} />
      {jobs.length === 0 ? (
        <div className="flex flex-col items-center px-4 py-10 text-center">
          <Cloud className="size-5 text-secondary" strokeWidth={1.5} />
          <div className="mt-3 text-sm font-medium">No deployments yet</div>
          <div className="text-[13px] text-secondary">Run a preflight or deploy above; every run lands here.</div>
        </div>
      ) : (
        <>
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-[760px] text-sm">
              <thead><tr className="text-left text-xs text-muted-foreground"><th className="px-4 py-2 font-medium">Status</th><th className="py-2 font-medium">Stage</th><th className="py-2 font-medium">Type</th><th className="py-2 font-medium">Version</th><th className="py-2 font-medium">Duration</th><th className="py-2 font-medium">Triggered by</th><th className="py-2 font-medium">Started</th><th className="py-2 pr-3 text-right font-medium">Actions</th></tr></thead>
              <tbody className="divide-y divide-border-subtle border-t border-border-subtle">
                {jobs.map((job) => {
                  const s = statusOf(job);
                  const expanded = open === job.id;
                  const error = errorOf(job);
                  const first = rowsOf(job)[0];
                  return [
                    <tr key={job.id} className={cn("align-middle", expanded && "bg-surface-hover/40")}>
                      <td className="px-4 py-2.5"><Badge tone={s.tone}>{s.label}</Badge></td>
                      <td className="whitespace-nowrap py-2.5 pr-4 font-mono">{job.stage ?? "dev"}</td>
                      <td className="whitespace-nowrap py-2.5 pr-4 text-secondary">{job.kind === "destroy" ? "Tear down" : job.dry_run ? "Preflight" : "Deploy"}</td>
                      <td className="whitespace-nowrap py-2.5 pr-4 font-mono">{versionOf(job) ?? "—"}</td>
                      <td className="whitespace-nowrap py-2.5 pr-4 font-mono text-secondary" suppressHydrationWarning>{duration(job, now)}</td>
                      <td className="max-w-0 truncate py-2.5 pr-4 text-secondary" title={job.by ?? undefined}>{job.by ?? "—"}</td>
                      <td className="whitespace-nowrap py-2.5 pr-4 text-secondary" suppressHydrationWarning>{when(job.created_at)}</td>
                      <td className="py-1.5 pr-3">
                        <div className="flex items-center justify-end gap-0.5">
                          <Menu label="Run actions" items={actions(job)} trigger={({ toggle, open: menuOpen, id }) => <Button size="icon" variant="ghost" aria-label="More actions" aria-haspopup="menu" aria-expanded={menuOpen} aria-controls={id} onClick={toggle}><MoreHorizontal className="size-4" strokeWidth={1.75} /></Button>} />
                          <Button size="icon" variant="ghost" aria-label={expanded ? "Collapse" : "Expand"} aria-expanded={expanded} onClick={() => setOpen(expanded ? null : job.id)}><ChevronDown className={cn("size-4 transition-transform", expanded && "rotate-180")} strokeWidth={1.75} /></Button>
                        </div>
                      </td>
                    </tr>,
                    expanded && (
                      <tr key={`${job.id}-details`} className="bg-surface-hover/40">
                        <td colSpan={8} className="px-4 pb-4 pt-1">
                          <RunDetails job={job} status={s} error={error} first={first ?? null} canDeploy={canDeploy} pending={pending} onDetails={() => setDetails(job)} onRedeploy={() => redeploy(job)} />
                        </td>
                      </tr>
                    ),
                  ];
                })}
              </tbody>
            </table>
          </div>
          <ul className="divide-y divide-border-subtle border-t border-border-subtle md:hidden">
            {jobs.map((job) => {
              const s = statusOf(job);
              const expanded = open === job.id;
              return (
                <li key={job.id} className="px-4 py-3 text-sm">
                  <div className="flex items-center gap-2">
                    <Badge tone={s.tone}>{s.label}</Badge>
                    <span className="font-mono">{job.stage ?? "dev"}</span>
                    <span className="text-secondary">{job.dry_run ? "preflight" : "deploy"}</span>
                    {versionOf(job) && <span className="font-mono text-secondary">{versionOf(job)}</span>}
                    <Button size="icon" variant="ghost" className="ml-auto" aria-label={expanded ? "Collapse" : "Expand"} aria-expanded={expanded} onClick={() => setOpen(expanded ? null : job.id)}><ChevronDown className={cn("size-4 transition-transform", expanded && "rotate-180")} strokeWidth={1.75} /></Button>
                  </div>
                  <div className="mt-1 text-xs text-secondary" suppressHydrationWarning>{duration(job, now)} · {job.by ?? "—"} · {when(job.created_at)}</div>
                  {expanded && <div className="mt-3"><RunDetails job={job} status={s} error={errorOf(job)} first={rowsOf(job)[0] ?? null} canDeploy={canDeploy} pending={pending} onDetails={() => setDetails(job)} onRedeploy={() => redeploy(job)} /></div>}
                </li>
              );
            })}
          </ul>
        </>
      )}

      <Dialog open={details !== null} onClose={() => setDetails(null)} title={details ? `Run ${details.id.slice(0, 8)}` : "Run"} description={details ? `${details.dry_run ? "Preflight" : "Deploy"} · ${details.stage ?? "dev"} · ${statusOf(details).label}` : undefined} className="max-w-2xl">
        {details && (
          <div className="space-y-4 text-sm">
            <dl className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3">
              <Item k="Run id" v={details.id} />
              <Item k="Version" v={versionOf(details) ?? "—"} />
              <Item k="Attempts" v={String(details.attempts)} />
              <Item k="Triggered by" v={details.by ?? "—"} />
              <Item k="Started" v={when(details.started_at ?? details.created_at)} />
              <Item k="Finished" v={when(details.finished_at)} />
            </dl>
            {errorOf(details) && <LogBox text={errorOf(details)!} />}
            {rowsOf(details).length > 0 && <LogBox text={JSON.stringify(rowsOf(details), null, 2)} />}
          </div>
        )}
      </Dialog>
    </Panel>
  );
}

function RunDetails({ job, status, error, first, canDeploy, pending, onDetails, onRedeploy }: { job: JobRow; status: Status; error: string | null; first: DeployResult | null; canDeploy: boolean; pending: boolean; onDetails: () => void; onRedeploy: () => void }) {
  const [logs, setLogs] = useState(false);
  const summary = error ? summarize(error) : first ? `${first.target} · ${first.version}${first.url ? ` · ${first.url}` : ""}` : status.label;
  return (
    <div className="space-y-3 rounded-md border border-border bg-surface p-3">
      <div className="flex flex-wrap items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium">{job.kind === "destroy" ? (error ? "Tear down failed" : status.label) : error ? (job.dry_run ? "Preflight failed" : "Deploy failed") : job.dry_run ? "Preflight passed" : status.label}</div>
          <div className="break-words text-[13px] text-secondary">{summary}</div>
          {first?.url && !error && <a href={first.url} target="_blank" rel="noopener noreferrer" className="mt-1 inline-flex items-center gap-1 text-[13px] text-secondary hover:text-foreground">{first.url} <ExternalLink className="size-3" strokeWidth={1.75} /></a>}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {error && <Button size="sm" variant="ghost" onClick={() => setLogs((v) => !v)} aria-expanded={logs}>{logs ? "Hide logs" : "View logs"}</Button>}
          {error && <CopyButton text={error} label="Copy error" />}
          <Button size="sm" variant="outline" onClick={onDetails}>View details</Button>
          {canDeploy && job.kind !== "destroy" && (job.version || first?.version) && <Button size="sm" variant="outline" disabled={pending} onClick={onRedeploy}><RotateCcw className="size-3.5" strokeWidth={1.75} /> {job.dry_run ? "Run again" : "Redeploy"}</Button>}
        </div>
      </div>
      {error && logs && <LogBox text={error} />}
      <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs sm:grid-cols-4">
        <Item k="Run id" v={job.id.slice(0, 8)} />
        <Item k="Started" v={when(job.started_at ?? job.created_at)} />
        <Item k="Finished" v={when(job.finished_at)} />
        <Item k="Attempts" v={String(job.attempts)} />
      </dl>
    </div>
  );
}

function Item({ k, v }: { k: string; v: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-secondary">{k}</dt>
      <dd className="truncate font-mono text-[13px]" title={v} suppressHydrationWarning>{v}</dd>
    </div>
  );
}
