"use client";

import { Cloud, ExternalLink, MoreHorizontal, RotateCcw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Menu } from "@/components/ui/menu";
import { Cell, DataTable } from "@/components/ui/data-table";
import type { DeployResult } from "@/lib/api";
import type { Paged } from "@/lib/page";
import type { JobRow } from "@/lib/v1";
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

export function DeploymentsTable({ page, registryId, canDeploy, newHref }: { page: Paged<JobRow>; registryId: string; canDeploy: boolean; newHref?: string | null }) {
  const jobs = page.items;
  const router = useRouter();
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
  const type = (job: JobRow) => (job.kind === "destroy" ? "Tear down" : job.dry_run ? "Preflight" : "Deploy");

  return (
    <>
      <DataTable
        title="Deployments"
        rows={jobs}
        paging={page}
        rowKey={(j) => j.id}
        noun={["run", "runs"]}
        newHref={canDeploy ? newHref : null}
        newLabel="New deployment"
        empty={{ icon: Cloud, title: "No deployments yet", text: "Run a preflight or deploy from New deployment; every run lands here." }}
        minWidth={880}
        columns={[
          { key: "status", label: "Status", width: 14, render: (job) => { const s = statusOf(job); return <Badge tone={s.tone}>{s.label}</Badge>; } },
          { key: "stage", label: "Stage", width: 9, render: (job) => <Cell mono>{job.stage ?? "dev"}</Cell> },
          { key: "type", label: "Type", width: 9, hide: "sm", render: (job) => <Cell muted>{type(job)}</Cell> },
          { key: "version", label: "Version", width: 15, render: (job) => <Cell mono>{versionOf(job) ?? "—"}</Cell> },
          { key: "duration", label: "Duration", width: 10, hide: "md", render: (job) => <span className="block truncate font-mono text-[13px] text-secondary" suppressHydrationWarning>{duration(job, now)}</span> },
          { key: "by", label: "Triggered by", width: 20, hide: "lg", render: (job) => <Cell muted title={job.by ?? undefined}>{job.by ?? "—"}</Cell> },
          { key: "started", label: "Started", width: 18, hide: "sm", render: (job) => <span className="block truncate text-secondary" suppressHydrationWarning>{when(job.created_at)}</span> },
          { key: "actions", label: "", width: 5, align: "right", render: (job) => <Menu label="Run actions" items={actions(job)} trigger={({ toggle, open, id }) => <Button size="icon" variant="ghost" aria-label="More actions" aria-haspopup="menu" aria-expanded={open} aria-controls={id} onClick={toggle}><MoreHorizontal className="size-4" strokeWidth={1.75} /></Button>} /> },
        ]}
      />

      <Dialog open={details !== null} onClose={() => setDetails(null)} title={details ? `Run ${details.id.slice(0, 8)}` : "Run"} description={details ? `${type(details)} · ${details.stage ?? "dev"} · ${statusOf(details).label}` : undefined} className="max-w-2xl">
        {details && (
          <div className="space-y-4 text-sm">
            <RunDetails job={details} status={statusOf(details)} error={errorOf(details)} first={rowsOf(details)[0] ?? null} canDeploy={canDeploy} pending={pending} onRedeploy={() => { redeploy(details); setDetails(null); }} />
            <dl className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3">
              <Item k="Run id" v={details.id} />
              <Item k="Version" v={versionOf(details) ?? "—"} />
              <Item k="Attempts" v={String(details.attempts)} />
              <Item k="Triggered by" v={details.by ?? "—"} />
              <Item k="Started" v={when(details.started_at ?? details.created_at)} />
              <Item k="Finished" v={when(details.finished_at)} />
            </dl>
            {rowsOf(details).length > 0 && <LogBox text={JSON.stringify(rowsOf(details), null, 2)} />}
          </div>
        )}
      </Dialog>
    </>
  );
}

function RunDetails({ job, status, error, first, canDeploy, pending, onRedeploy }: { job: JobRow; status: Status; error: string | null; first: DeployResult | null; canDeploy: boolean; pending: boolean; onRedeploy: () => void }) {
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
      {redeployable && <div className="flex justify-end"><Button variant="outline" size="sm" disabled={pending} onClick={onRedeploy}><RotateCcw className="size-3.5" strokeWidth={1.75} /> {job.dry_run ? "Run again" : "Redeploy"}</Button></div>}
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
