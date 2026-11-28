"use client";

import { Check, Copy, ExternalLink, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CopyButton, LogBox } from "@/components/ui/copy-button";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import type { DeployResult } from "@/lib/api";
import type { JobRow } from "@/lib/v1";
import { LiveLog } from "@/features/jobs";
import { startDeploy } from "./actions";
import { canRedeploy, elapsed, errorOf, releaseTag, rowsOf, statusOf, typeOf, versionOf, when } from "./job-state";
import { summarize } from "./run-alert";
import { RolloutPanel, type RolloutView } from "./rollout-panel";
import { ACTIVE_STATES, STATE_LABELS, STATE_TONES } from "./strategies";

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

function Results({ rows }: { rows: DeployResult[] }) {
  return (
    <Panel>
      <PanelHeader title="Targets" />
      <ul className="divide-y divide-border-subtle">
        {rows.map((r, i) => (
          <li key={`${r.target}-${i}`} className="space-y-1 px-4 py-2.5 text-[13px]">
            <div className="flex min-w-0 items-center gap-2">
              <Badge tone={r.ok ? "success" : "danger"}>{r.ok ? "Shipped" : "Failed"}</Badge>
              <span className="font-medium">{r.target}</span>
              {r.version && <span className="font-mono text-xs text-secondary">{r.version}</span>}
            </div>
            {r.error && <p className="break-words text-secondary">{summarize(r.error)}</p>}
          </li>
        ))}
      </ul>
    </Panel>
  );
}

export function DeploymentView({ job, base, projectId, appId, registryId, canDeploy, rollouts = [], children }: { job: JobRow; base: string; projectId: string; appId: string; registryId: string; canDeploy: boolean; rollouts?: RolloutView[]; children?: ReactNode }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const rows = rowsOf(job);
  const headline = rollouts.find((r) => ACTIVE_STATES.includes(r.status)) ?? rollouts[0] ?? null;
  const status = headline ? { tone: STATE_TONES[headline.status] ?? "neutral", label: STATE_LABELS[headline.status] ?? headline.status } : statusOf(job);
  const failure = errorOf(job);
  const kind = typeOf(job);
  const version = versionOf(job);
  const live = job.status === "queued" || job.status === "running" || rollouts.some((r) => ACTIVE_STATES.includes(r.status));
  const first = rows[0] ?? null;

  useEffect(() => {
    if (!live) return;
    const timer = setInterval(() => { setNow(Date.now()); router.refresh(); }, 4000);
    return () => clearInterval(timer);
  }, [live, router]);

  const redeploy = () =>
    start(async () => {
      setError(null);
      const r = await startDeploy(projectId, registryId, job.stage ?? "", !!job.dry_run, job.version ?? version ?? "");
      if (!r.ok) { setError(r.error); return; }
      router.push(`${base}/deployments${"job" in r.data ? `/${encodeURIComponent(r.data.job)}` : ""}`);
    });

  return (
    <div className="space-y-4">
      <Panel>
        <PanelHeader
          title={<>{kind} <span className="font-mono font-normal text-secondary">{job.id.slice(0, 8)}</span><Badge tone={status.tone}>{status.label}</Badge></>}
          aside={canRedeploy(job, canDeploy) ? (
            <Button variant="outline" size="sm" onClick={redeploy} loading={pending} disabled={pending || live}>
              <RotateCcw className="size-3.5" strokeWidth={1.75} /> {pending ? "Redeploying…" : job.dry_run ? "Run again" : "Redeploy"}
            </Button>
          ) : undefined}
        />
        <PanelBody className="space-y-5 text-sm">
          {error && <div className="rounded-md border border-border px-3 py-2 text-[13px] text-secondary">{error}</div>}
          <dl className="grid grid-cols-1 gap-x-6 gap-y-3 min-[400px]:grid-cols-2 sm:grid-cols-4">
            <Field label="Stage">{job.stage ?? "—"}</Field>
            <Field label="Type">{kind}</Field>
            <Field label="Version">{version ? <Link href={`${base}/releases/${encodeURIComponent(releaseTag(version))}`} className="font-mono hover:underline underline-offset-4">{version}</Link> : "—"}</Field>
            <Field label="By">{job.by ?? "—"}</Field>
            <Field label="Started">{when(job.started_at ?? job.created_at)}</Field>
            <Field label="Finished">{when(job.finished_at)}</Field>
            <Field label="Duration">{elapsed(job, now)}</Field>
            <Field label="Attempts">{String(job.attempts)}</Field>
          </dl>
          {failure && (
            <section className="rounded-lg border border-border border-l-2 border-l-status-bad bg-surface px-3 py-2.5">
              <div className="text-sm font-medium">{kind} failed</div>
              <div className="break-words text-[13px] text-secondary">{summarize(failure)}</div>
              <div className="mt-2"><LogBox text={failure} /></div>
            </section>
          )}
          {first?.url && !failure && <Endpoint url={first.url} />}
        </PanelBody>
      </Panel>
      {rollouts.map((r) => <RolloutPanel key={r.id} projectId={projectId} appId={appId} rollout={r} canDeploy={canDeploy} />)}
      {rows.length > 0 && <Results rows={rows} />}
      {children}
      <Panel>
        <PanelBody><LiveLog jobId={job.id} live={live} title="Platform log" maxHeight="max-h-[28rem]" /></PanelBody>
      </Panel>
      {rows.length > 0 && <Panel><PanelBody><Output rows={rows} /></PanelBody></Panel>}
    </div>
  );
}
