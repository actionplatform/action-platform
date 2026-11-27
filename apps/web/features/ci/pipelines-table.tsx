"use client";

import { Workflow } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Cell, DataTable, Inline } from "@/components/ui/data-table";
import { Select } from "@/components/ui/select";
import { CI_LABELS, type Pipelines, type PipelineRun, duration, runHref } from "@/lib/ci-kinds";
import { relativeTime } from "@/lib/time";
import { RunBadge, RunIcon } from "./run-badge";

const STATUSES = [
  { value: "", label: "Any status" },
  { value: "running", label: "Running" },
  { value: "queued", label: "Queued" },
  { value: "success", label: "Passed" },
  { value: "failure", label: "Failed" },
  { value: "unstable", label: "Unstable" },
  { value: "aborted", label: "Aborted" },
];

const KIND_LABEL: Record<string, string> = { ci: "CI", cd: "CD", scheduled: "Scheduled" };

type Props = { base: string; data: Pipelines; job: string; status: string; connectHref: string | null };

export function PipelinesTable({ base, data, job, status, connectHref }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const connected = data.kind !== "none";
  const labels = new Map(data.jobs.map((j) => [j.name, j]));

  const filter = (key: "job" | "status", value: string) => {
    const q = new URLSearchParams(params.toString());
    if (value) q.set(key, value);
    else q.delete(key);
    router.replace(`${pathname}${q.size ? `?${q.toString()}` : ""}`, { scroll: false });
  };

  const title = (r: PipelineRun) => (r.name && r.name !== `#${r.number}` ? r.name : `#${r.number}`);

  return (
    <div className="space-y-3">
      {data.errors.map((e) => (
        <div key={e.job} className="rounded-md border border-border px-3 py-2 text-[13px] text-secondary"><span className="font-mono">{e.job || "CI"}</span>: {e.error}</div>
      ))}
      <DataTable
        title="Pipelines"
        rows={data.runs}
        rowKey={(r) => `${r.job}#${r.number}`}
        noun={["run", "runs"]}
        meta={connected ? CI_LABELS[data.kind] ?? data.kind : undefined}
        action={
          connected && data.jobs.length > 0 ? (
            <div className="flex flex-wrap items-center gap-2">
              <Select size="sm" aria-label="Job" value={job} onChange={(v) => filter("job", v)} options={[{ value: "", label: "Every job" }, ...data.jobs.map((j) => ({ value: j.name, label: j.label, hint: j.name || undefined }))]} className="w-48" />
              <Select size="sm" aria-label="Status" value={status} onChange={(v) => filter("status", v)} options={STATUSES} className="w-36" />
            </div>
          ) : undefined
        }
        newHref={connected ? null : connectHref}
        newLabel="Connect CI"
        empty={{
          icon: Workflow,
          title: !connected ? "No CI connected" : data.jobs.length === 0 ? "No pipelines" : "No runs",
          text: !connected
            ? "Connect a runner to follow this app's pipelines here."
            : data.jobs.length === 0
              ? "Name the app's CI job in its settings, or a job on a deploy target, to follow its runs here."
              : "No run matches the filters.",
        }}
        columns={[
          { key: "status", label: "Status", width: 11, render: (r) => <Inline><RunIcon status={r.status} /><RunBadge status={r.status} /></Inline> },
          { key: "run", label: "Run", width: 30, render: (r) => <Inline><Link href={runHref(base, r.job, r.number)} className="min-w-0 truncate font-medium hover:underline underline-offset-4" title={title(r)}>{title(r)}</Link>{r.name && r.name !== `#${r.number}` && <span className="shrink-0 font-mono text-xs text-muted-foreground">#{r.number}</span>}</Inline> },
          { key: "job", label: "Job", width: 16, render: (r) => <Inline><span className="shrink-0 rounded border border-border px-1.5 text-[11px] text-secondary">{KIND_LABEL[labels.get(r.job)?.kind ?? "ci"]}</span><Cell mono muted title={r.job}>{labels.get(r.job)?.label ?? r.job}</Cell></Inline> },
          { key: "branch", label: "Ref", width: 12, hideBelow: "lg", render: (r) => <Cell mono muted title={r.branch ?? undefined}>{r.branch ?? "—"}</Cell> },
          { key: "trigger", label: "Trigger", width: 11, hideBelow: "lg", render: (r) => <Cell muted title={r.trigger ?? undefined}>{r.trigger ?? "—"}</Cell> },
          { key: "when", label: "Started", width: 10, hideBelow: "md", render: (r) => <Cell muted>{r.startedAt ? relativeTime(r.startedAt) : "—"}</Cell> },
          { key: "duration", label: "Duration", width: 10, numeric: true, hideBelow: "md", render: (r) => <Cell muted>{duration(r.durationMs)}</Cell> },
        ]}
      />
    </div>
  );
}
