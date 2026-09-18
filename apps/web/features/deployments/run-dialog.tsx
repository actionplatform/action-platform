"use client";

import { Check, Copy, ExternalLink, RotateCcw } from "lucide-react";
import { type ReactNode, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import type { DeployResult } from "@/lib/api";
import type { JobRow } from "@/lib/v1";
import { LiveLog } from "@/features/jobs";
import { CopyButton, LogBox } from "@/components/ui/copy-button";
import { summarize } from "./run-alert";

export type Status = { tone: "danger" | "warning" | "success" | "neutral"; label: string };

function when(d: string | null | undefined): string {
  if (!d) return "—";
  const t = new Date(d);
  return Number.isNaN(t.getTime()) ? d : t.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function Field({ label, children, className }: { label: string; children: ReactNode; className?: string }) {
  return (
    <div className={`min-w-0 ${className ?? ""}`}>
      <dt className="text-xs text-secondary">{label}</dt>
      <dd className="mt-0.5 truncate text-sm font-medium" title={typeof children === "string" ? children : undefined} suppressHydrationWarning>{children}</dd>
    </div>
  );
}

function Endpoint({ url }: { url: string }) {
  const [done, setDone] = useState(false);
  const copy = async () => {
    try { await navigator.clipboard.writeText(url); setDone(true); setTimeout(() => setDone(false), 1500); } catch { setDone(false); }
  };
  return (
    <section className="min-w-0">
      <div className="mb-1.5 text-xs text-secondary">Endpoint</div>
      <div className="flex min-w-0 items-center gap-1 rounded-lg border border-border bg-background pl-3 pr-1">
        <span className="min-w-0 flex-1 select-none truncate py-2 font-mono text-[13px] leading-5 sm:whitespace-nowrap" title={url}>{url}</span>
        <span className="flex shrink-0 items-center">
          <Button size="icon" variant="ghost" aria-label={done ? "Copied" : "Copy endpoint"} onClick={copy} className="size-9 sm:size-8">{done ? <Check className="size-3.5" strokeWidth={2.5} /> : <Copy className="size-3.5" strokeWidth={1.75} />}</Button>
          <a href={url} target="_blank" rel="noopener noreferrer" aria-label="Open endpoint in a new tab" className="inline-flex size-9 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground sm:size-8"><ExternalLink className="size-3.5" strokeWidth={1.75} /></a>
        </span>
      </div>
      {done && <div className="mt-1 text-xs text-status-ok" role="status">Copied</div>}
    </section>
  );
}

const TOKEN = /("(?:\\.|[^"\\])*")(\s*:)?|\b(true|false|null)\b|(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)/gi;

function Json({ value }: { value: unknown }) {
  const text = JSON.stringify(value, null, 2);
  const parts: ReactNode[] = [];
  let last = 0;
  let i = 0;
  for (const m of text.matchAll(TOKEN)) {
    const at = m.index ?? 0;
    if (at > last) parts.push(text.slice(last, at));
    if (m[1] !== undefined) {
      parts.push(<span key={i++} className={m[2] ? "text-foreground" : "text-status-ok/90"}>{m[1]}</span>);
      if (m[2]) parts.push(m[2]);
    } else if (m[3] !== undefined) {
      parts.push(<span key={i++} className="text-status-warn/90">{m[3]}</span>);
    } else if (m[4] !== undefined) {
      parts.push(<span key={i++} className="text-foreground/80">{m[4]}</span>);
    }
    last = at + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return <>{parts}</>;
}

function Output({ rows }: { rows: DeployResult[] }) {
  const value = rows.length === 1 ? rows[0] : rows;
  return (
    <section className="min-w-0">
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="text-xs text-secondary">Deployment output</span>
        <CopyButton text={JSON.stringify(value, null, 2)} label="Copy output" size="icon" />
      </div>
      <pre className="max-h-56 overflow-auto rounded-lg border border-border bg-background p-3 font-mono text-xs leading-5 text-secondary [overflow-wrap:anywhere] whitespace-pre-wrap"><Json value={value} /></pre>
    </section>
  );
}

export function RunDialog({ job, status, error, rows, kindLabel, canRedeploy, redeploying, onRedeploy, onClose }: {
  job: JobRow | null;
  status: Status | null;
  error: string | null;
  rows: DeployResult[];
  kindLabel: string;
  canRedeploy: boolean;
  redeploying: boolean;
  onRedeploy: () => void;
  onClose: () => void;
}) {
  const first = rows[0] ?? null;
  const live = !!job && (job.status === "queued" || job.status === "running");
  const version = first?.version || job?.version || null;
  const target = first?.target ?? null;

  return (
    <Dialog
      open={job !== null}
      onClose={() => { if (!redeploying) onClose(); }}
      title={job ? <span className="inline-flex flex-wrap items-center gap-2">Run {job.id.slice(0, 8)}{status && <Badge tone={status.tone}>{status.label}</Badge>}</span> : "Run"}
      description={job ? `${kindLabel} · ${job.stage ?? "dev"}` : undefined}
      className="sm:max-w-[720px]"
      footer={
        canRedeploy ? (
          <Button variant="outline" onClick={onRedeploy} loading={redeploying} disabled={redeploying} className="w-full sm:w-auto">
            <RotateCcw className="size-3.5" strokeWidth={1.75} /> {redeploying ? "Redeploying…" : job?.dry_run ? "Run again" : "Redeploy"}
          </Button>
        ) : undefined
      }
    >
      {job && (
        <div className="space-y-5 text-sm">
          <dl className="grid grid-cols-1 gap-x-6 gap-y-3 min-[400px]:grid-cols-2 sm:grid-cols-3">
            <Field label="Target">{target ?? "—"}</Field>
            <Field label="Version">{version ? <span className="font-mono">{version}</span> : "—"}</Field>
            <Field label="Attempts">{String(job.attempts)}</Field>
            <Field label="Started">{when(job.started_at ?? job.created_at)}</Field>
            <Field label="Finished">{when(job.finished_at)}</Field>
            <Field label="By">{job.by ?? "—"}</Field>
          </dl>
          {error && (
            <section className="rounded-lg border border-border border-l-2 border-l-status-bad bg-surface px-3 py-2.5">
              <div className="text-sm font-medium">{kindLabel} failed</div>
              <div className="break-words text-[13px] text-secondary">{summarize(error)}</div>
              <div className="mt-2"><LogBox text={error} /></div>
            </section>
          )}
          {first?.url && !error && <Endpoint url={first.url} />}
          <LiveLog jobId={job.id} live={live} />
          {rows.length > 0 && <Output rows={rows} />}
        </div>
      )}
    </Dialog>
  );
}
