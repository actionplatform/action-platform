"use client";

import { Cloud, MoreHorizontal, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Menu } from "@/components/ui/menu";
import { Cell, DataTable } from "@/components/ui/data-table";
import type { Paged } from "@/lib/page";
import type { JobRow } from "@/lib/v1";
import { startDeploy } from "@/features/deployments/actions";
import { canRedeploy, deploymentHref, elapsed, statusOf, typeOf, versionOf, when } from "./job-state";

export function DeploymentsTable({ page, projectId, registryId, canDeploy, base, newHref }: { page: Paged<JobRow>; projectId: string; registryId: string; canDeploy: boolean; base: string; newHref?: string | null }) {
  const jobs = page.items;
  const router = useRouter();
  const [now, setNow] = useState(() => Date.now());
  const [pending, start] = useTransition();
  const live = jobs.some((j) => j.status === "running" || j.status === "queued");

  useEffect(() => {
    if (!live) return;
    const timer = setInterval(() => { setNow(Date.now()); router.refresh(); }, 4000);
    return () => clearInterval(timer);
  }, [live, router]);

  const redeploy = (job: JobRow) => {
    if (pending) return;
    start(async () => {
      const r = await startDeploy(projectId, registryId, job.stage ?? "", !!job.dry_run, job.version ?? versionOf(job) ?? "");
      if (r.ok) router.refresh();
    });
  };

  const actions = (job: JobRow) => [
    { label: "View details", onSelect: () => router.push(deploymentHref(base, job.id)) },
    ...(canRedeploy(job, canDeploy) ? [{ label: job.dry_run ? "Run preflight again" : "Redeploy", icon: <RotateCcw className="size-3.5" strokeWidth={1.75} />, onSelect: () => redeploy(job) }] : []),
  ];

  return (
    <DataTable
      title="Deployments"
      rows={jobs}
      paging={page}
      rowKey={(j) => j.id}
      rowHref={(j) => deploymentHref(base, j.id)}
      noun={["run", "runs"]}
      newHref={canDeploy ? newHref : null}
      newLabel="New deployment"
      empty={{ icon: Cloud, title: "No deployments yet", text: "Run a preflight or deploy from New deployment; every run lands here." }}
      columns={[
        { key: "status", label: "Status", width: 14, render: (job) => { const s = statusOf(job); return <Link href={deploymentHref(base, job.id)} aria-label={`Open run ${job.id.slice(0, 8)}`} className="rounded-full focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground"><Badge tone={s.tone}>{s.label}</Badge></Link>; } },
        { key: "stage", label: "Stage", width: 9, render: (job) => <Cell mono>{job.stage ?? "—"}</Cell> },
        { key: "type", label: "Type", width: 9, hideBelow: "md", render: (job) => <Cell muted>{typeOf(job)}</Cell> },
        { key: "version", label: "Version", width: 15, render: (job) => <Cell mono>{versionOf(job) ?? "—"}</Cell> },
        { key: "duration", label: "Duration", width: 10, numeric: true, hideBelow: "md", render: (job) => <Cell muted>{elapsed(job, now)}</Cell> },
        { key: "by", label: "By", width: 20, hideBelow: "lg", render: (job) => <Cell muted title={job.by ?? undefined}>{job.by ?? "—"}</Cell> },
        { key: "started", label: "Started", width: 18, hideBelow: "md", render: (job) => <Cell muted>{when(job.created_at)}</Cell> },
        { key: "actions", label: "Actions", width: 5, actions: true, render: (job) => <Menu label="Run actions" items={actions(job)} trigger={({ toggle, open, id }) => <Button size="icon" variant="ghost" aria-label="More actions" aria-haspopup="menu" aria-expanded={open} aria-controls={id} onClick={toggle}><MoreHorizontal className="size-4" strokeWidth={1.75} /></Button>} /> },
      ]}
    />
  );
}
