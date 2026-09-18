"use client";

import { ChevronDown, Cloud, ExternalLink, MoreHorizontal, Plus, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Menu } from "@/components/ui/menu";
import { Pagination, usePagination } from "@/components/ui/pagination";
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

export function DeploymentsTable({ jobs: all, registryId, canDeploy, newHref }: { jobs: JobRow[]; registryId: string; canDeploy: boolean; newHref?: string | null }) {
  const router = useRouter();
  const paging = usePagination(all, "runs");
  const jobs = paging.rows;
  const [open, setOpen] = useState<string | null>(null);
  const [details, setDetails] = useState<JobRow | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [pending, start] = useTransition();
  const live = all.some((j) => j.status === "running" || j.status === "queued");

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
      <PanelHeader
        title="Deployments"
        aside={
          <div className="flex items-center gap-3">
            <span className="hidden text-[13px] text-secondary sm:block">{all.length} {all.length === 1 ? "run" : "runs"}</span>
            {newHref && canDeploy && <Link href={newHref} className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border px-3 text-sm font-medium hover:border-border-hover hover:bg-surface-hover"><Plus className="size-3.5" strokeWidth={2} /> New deployment</Link>}
          </div>
        }
      />
      {all.length === 0 ? (
        <div className="flex flex-col items-center px-4 py-10 text-center">
          <Cloud className="size-5 text-secondary" strokeWidth={1.5} />
          <div className="mt-3 text-sm font-medium">No deployments yet</div>
          <div className="text-[13px] text-secondary">Run a preflight or deploy from New deployment; every run lands here.</div>
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
                <li key={job.id} className="min-w-0 px-4 py-3 text-sm">
                  <button type="button" className="flex min-h-11 w-full min-w-0 items-center gap-2 text-left focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground rounded-sm" aria-expanded={expanded} onClick={() => setOpen(expanded ? null : job.id)}>
                    <Badge tone={s.tone}>{s.label}</Badge>
                    <span className="font-mono">{job.stage ?? "dev"}</span>
                    <span className="text-secondary">{job.kind === "destroy" ? "tear down" : job.dry_run ? "preflight" : "deploy"}</span>
                    {versionOf(job) && <span className="truncate font-mono text-secondary">{versionOf(job)}</span>}
                    <ChevronDown className={cn("ml-auto size-4 shrink-0 text-secondary transition-transform", expanded && "rotate-180")} strokeWidth={1.75} aria-hidden="true" />
                  </button>
                  <div className="mt-1 flex flex-wrap gap-x-1.5 text-xs text-secondary" suppressHydrationWarning><span>{duration(job, now)}</span><span aria-hidden="true">·</span><span className="min-w-0 break-all">{job.by ?? "—"}</span><span aria-hidden="true">·</span><span className="whitespace-nowrap">{when(job.created_at)}</span></div>
                  {expanded && <div className="mt-3"><RunDetails job={job} status={s} error={errorOf(job)} first={rowsOf(job)[0] ?? null} canDeploy={canDeploy} pending={pending} onDetails={() => setDetails(job)} onRedeploy={() => redeploy(job)} /></div>}
                </li>
              );
            })}
          </ul>
          <Pagination page={paging.page} pages={paging.pages} per={paging.per} total={paging.total} onPage={paging.setPage} onPer={paging.setPer} noun={["run", "runs"]} />
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
  const title = job.kind === "destroy" ? (error ? "Tear down failed" : status.label) : error ? (job.dry_run ? "Preflight failed" : "Deploy failed") : job.dry_run ? "Preflight passed" : status.label;
  const redeployable = canDeploy && job.kind !== "destroy" && !!(job.version || first?.version);
  return (
    <div className="min-w-0 space-y-3 rounded-md border border-border bg-surface p-3">
      <div className="min-w-0">
        <div className="text-sm font-medium">{title}</div>
        {error ? (
          <div className="break-words text-[13px] text-secondary">{summarize(error)}</div>
        ) : first ? (
          <div className="text-[13px]"><span className="font-medium">{first.target}</span>{first.version && <span className="text-secondary"> · {first.version}</span>}</div>
        ) : null}
      </div>
      {first?.url && !error && (
        <div className="min-w-0">
          <div className="mb-1 text-xs text-secondary">Endpoint</div>
          <div className="flex min-w-0 items-center gap-1 rounded-md border border-border bg-background pl-3 pr-1">
            <a href={first.url} target="_blank" rel="noopener noreferrer" className="min-w-0 flex-1 py-2 font-mono text-[13px] leading-5 [overflow-wrap:anywhere] line-clamp-2 hover:text-foreground">{first.url}</a>
            <CopyButton text={first.url} label="Copy endpoint" size="icon" />
            <a href={first.url} target="_blank" rel="noopener noreferrer" aria-label="Open endpoint" className="inline-flex size-11 shrink-0 items-center justify-center rounded-md text-secondary hover:text-foreground md:size-8"><ExternalLink className="size-4" strokeWidth={1.75} /></a>
          </div>
        </div>
      )}
      {error && (
        <div className="flex flex-wrap items-center gap-1.5">
          <Button size="sm" variant="ghost" onClick={() => setLogs((v) => !v)} aria-expanded={logs}>{logs ? "Hide logs" : "View logs"}</Button>
          <CopyButton text={error} label="Copy error" />
        </div>
      )}
      {error && logs && <LogBox text={error} />}
      <dl className="grid grid-cols-[repeat(2,minmax(0,1fr))] gap-x-4 gap-y-2 text-xs sm:grid-cols-4">
        <Item k="Run id" v={job.id.slice(0, 8)} />
        <Item k="Started" v={when(job.started_at ?? job.created_at)} />
        <Item k="Finished" v={when(job.finished_at)} />
        <Item k="Attempts" v={String(job.attempts)} />
      </dl>
      <div className="grid grid-cols-1 gap-2 min-[360px]:grid-cols-2 md:flex md:justify-end">
        <Button variant="outline" className="min-h-11 w-full md:h-8 md:min-h-0 md:w-auto" onClick={onDetails}>View details</Button>
        {redeployable && <Button variant="outline" className="min-h-11 w-full md:h-8 md:min-h-0 md:w-auto" disabled={pending} onClick={onRedeploy}><RotateCcw className="size-3.5" strokeWidth={1.75} /> {job.dry_run ? "Run again" : "Redeploy"}</Button>}
      </div>
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
