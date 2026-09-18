"use client";

import { Cloud, MoreHorizontal, RotateCcw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Menu } from "@/components/ui/menu";
import { Cell, DataTable } from "@/components/ui/data-table";
import type { DeployResult } from "@/lib/api";
import type { Paged } from "@/lib/page";
import type { JobRow } from "@/lib/v1";
import { startDeploy } from "@/features/deployments/actions";
import { RunDialog, type Status } from "./run-dialog";

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

  const redeploy = (job: JobRow, close = false) => {
    if (pending) return;
    start(async () => {
      const r = await startDeploy(registryId, job.stage ?? "dev", !!job.dry_run, job.version ?? versionOf(job) ?? "");
      if (r.ok) { if (close) setDetails(null); router.refresh(); }
    });
  };

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
          { key: "duration", label: "Duration", width: 10, hide: "sm", render: (job) => <span className="block truncate font-mono text-[13px] text-secondary" suppressHydrationWarning>{duration(job, now)}</span> },
          { key: "by", label: "By", width: 20, hide: "md", render: (job) => <Cell muted title={job.by ?? undefined}>{job.by ?? "—"}</Cell> },
          { key: "started", label: "Started", width: 18, hide: "sm", render: (job) => <span className="block truncate text-secondary" suppressHydrationWarning>{when(job.created_at)}</span> },
          { key: "actions", label: "", width: 5, align: "right", render: (job) => <Menu label="Run actions" items={actions(job)} trigger={({ toggle, open, id }) => <Button size="icon" variant="ghost" aria-label="More actions" aria-haspopup="menu" aria-expanded={open} aria-controls={id} onClick={toggle}><MoreHorizontal className="size-4" strokeWidth={1.75} /></Button>} /> },
        ]}
      />

      <RunDialog
        job={details}
        status={details ? statusOf(details) : null}
        error={details ? errorOf(details) : null}
        rows={details ? rowsOf(details) : []}
        kindLabel={details ? type(details) : ""}
        canRedeploy={!!details && canDeploy && details.kind !== "destroy" && !!(details.version || versionOf(details))}
        redeploying={pending}
        onRedeploy={() => { if (details) redeploy(details, true); }}
        onClose={() => setDetails(null)}
      />
    </>
  );
}

