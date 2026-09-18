"use client";

import { Ban, Check, CircleDashed, ExternalLink, LoaderCircle, Plus, RefreshCw, ShieldCheck, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { Select } from "@/components/ui/select";
import { type Deployment, type DeploymentStatus, type DeploymentsState, EXECUTOR_LABELS, KIND_LABELS, type Target, liveOf } from "@/lib/deployments-kinds";
import { relativeTime } from "@/lib/time";
import { call } from "@/lib/call";
import { recordDeployment, syncDeployments } from "./records-actions";

const STATUS: Record<DeploymentStatus, { label: string; tone: "success" | "danger" | "warning" | "neutral"; icon: typeof Check; spin?: boolean }> = {
  verified: { label: "Verified", tone: "success", icon: ShieldCheck },
  success: { label: "Shipped", tone: "success", icon: Check },
  failure: { label: "Failed", tone: "danger", icon: X },
  running: { label: "Running", tone: "warning", icon: LoaderCircle, spin: true },
  queued: { label: "Queued", tone: "neutral", icon: CircleDashed },
};

function StatusBadge({ status }: { status: DeploymentStatus }) {
  const meta = STATUS[status] ?? STATUS.queued;
  const Icon = meta.icon;
  return <Badge tone={meta.tone} className="h-5 gap-1 px-2 text-[11px]"><Icon className={`size-3 ${meta.spin ? "animate-spin" : ""}`} strokeWidth={2.5} /> {meta.label}</Badge>;
}

function Row({ d }: { d: Deployment }) {
  return (
    <li className="flex items-start gap-3 px-4 py-2.5">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-sm font-medium">{d.version}</span>
          {d.stage && <Badge className="h-5 px-2 text-[11px]">{d.stage}</Badge>}
          <StatusBadge status={d.status} />
          <span className="text-xs text-secondary">{EXECUTOR_LABELS[d.executor] ?? d.executor}</span>
        </div>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-secondary">
          {d.sha && <span className="font-mono">{d.sha.slice(0, 7)}</span>}
          {d.actor && <><span aria-hidden>·</span><span className="truncate">{d.actor}</span></>}
          {(d.finishedAt ?? d.startedAt) && <><span aria-hidden>·</span><span>{relativeTime((d.finishedAt ?? d.startedAt)!)}</span></>}
          {d.error && <><span aria-hidden>·</span><span className="truncate text-status-bad">{d.error}</span></>}
        </div>
      </div>
      {d.url && <a href={d.url} target="_blank" rel="noopener noreferrer" aria-label={`Open ${d.version}`} className="text-secondary hover:text-foreground"><ExternalLink className="size-4" strokeWidth={1.75} /></a>}
    </li>
  );
}

function TargetBlock({ target, rows, canRecord, onRecord }: { target: Target; rows: Deployment[]; canRecord: boolean; onRecord: (t: Target) => void }) {
  const mine = rows.filter((d) => d.target === target.name);
  const live = liveOf(target, rows);
  const source = target.workflow ?? target.job;
  return (
    <Panel>
      <PanelHeader
        title={target.name}
        aside={
          <div className="flex items-center gap-2 text-[13px] text-secondary">
            <span>{KIND_LABELS[target.kind] ?? target.kind}</span>
            <span aria-hidden>·</span>
            <span>{EXECUTOR_LABELS[target.runBy] ?? target.runBy}{source && <span className="font-mono"> · {source}</span>}</span>
            {canRecord && target.runBy === "manual" && <Button size="sm" variant="ghost" onClick={() => onRecord(target)} aria-label={`Record a deployment to ${target.name}`}><Plus className="size-3.5" strokeWidth={2} /></Button>}
          </div>
        }
      />
      <dl className={`grid gap-4 px-4 py-3 text-sm ${live.length > 1 ? "grid-cols-2 sm:grid-cols-4" : "grid-cols-1"}`}>
        {live.map((l) => (
          <div key={l.stage ?? "_"}>
            <dt className="text-xs text-secondary">{l.stage ?? "Live"}</dt>
            <dd className="mt-0.5 flex items-center gap-2"><span className="font-mono font-medium">{l.version}</span>{l.version !== "—" && <StatusBadge status={l.status} />}</dd>
          </div>
        ))}
      </dl>
      {mine.length === 0 ? (
        <div className="border-t border-border-subtle px-4 py-6 text-center text-[13px] text-secondary">
          {target.runBy === "platform" ? "Nothing shipped yet — deploy a release above." : target.runBy === "manual" ? "Nothing recorded yet." : `No run of ${source ?? "the pipeline"} on a release tag yet. Sync to look again.`}
        </div>
      ) : (
        <ul className="divide-y divide-border-subtle border-t border-border-subtle">{mine.slice(0, 10).map((d) => <Row key={d.id} d={d} />)}</ul>
      )}
    </Panel>
  );
}

type Props = { projectId: string; appId: string; state: DeploymentsState; canSync: boolean; canRecord: boolean };

export function TargetsPanel({ projectId, appId, state: initial, canSync, canRecord }: Props) {
  const router = useRouter();
  const [state, setState] = useState(initial);
  const [error, setError] = useState<string | null>(initial.error);
  const [status, setStatus] = useState<"idle" | "syncing" | "done">("idle");
  const [recording, setRecording] = useState<Target | null>(null);
  const [version, setVersion] = useState("");
  const [stage, setStage] = useState("");
  const [url, setUrl] = useState("");
  const [ok, setOk] = useState(true);
  const [pending, start] = useTransition();
  const observed = state.targets.some((t) => t.runBy === "github_actions" || t.runBy === "jenkins");

  const sync = () =>
    start(async () => {
      setStatus("syncing");
      const r = await call(() => syncDeployments(projectId, appId), (e) => ({ ok: false as const, error: e }), "Reload the page to see the current state.");
      if (!r.ok) { setError(r.error); setStatus("idle"); return; }
      setState(r.data);
      setError(r.data.error);
      setStatus("done");
      setTimeout(() => setStatus("idle"), 2500);
    });

  const record = () =>
    start(async () => {
      if (!recording) return;
      setError(null);
      const r = await call(() => recordDeployment(projectId, appId, { target: recording.name, version: version.trim(), stage: stage || null, url: url.trim() || null, ok }), (e) => ({ ok: false as const, error: e }), "Reload the page to see the current state.");
      if (!r.ok) { setError(r.error); return; }
      setState((s) => ({ ...s, deployments: [r.data, ...s.deployments] }));
      setRecording(null); setVersion(""); setStage(""); setUrl(""); setOk(true);
      router.refresh();
    });

  if (state.targets.length === 0) return null;

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold">Targets</h2>
        {canSync && observed && (
          <Button size="sm" variant="outline" onClick={sync} disabled={pending}>
            <RefreshCw className={`size-3.5 ${status === "syncing" ? "animate-spin" : ""}`} strokeWidth={2} /> {status === "syncing" ? "Syncing…" : status === "done" ? "Synced" : "Sync"}
          </Button>
        )}
      </div>
      {error && <div className="rounded-md border border-border px-3 py-2 text-[13px] text-secondary">{error}</div>}
      {recording && (
        <Panel>
          <PanelHeader title={`Record a deployment to ${recording.name}`} aside={<Button size="sm" variant="ghost" onClick={() => setRecording(null)} aria-label="Cancel"><X className="size-3.5" strokeWidth={2} /></Button>} />
          <PanelBody className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Release" hint="A tag: 1.4.0 or v1.4.0."><Input value={version} onChange={(e) => setVersion(e.target.value)} className="font-mono" placeholder="1.4.0" /></Field>
              {recording.stages.length > 0 && <Field label="Stage"><Select value={stage} onChange={setStage} options={recording.stages.map((s) => ({ value: s, label: s }))} placeholder="Pick a stage" aria-label="Stage" /></Field>}
              <Field label="URL" hint="Where it can be seen, if anywhere."><Input value={url} onChange={(e) => setUrl(e.target.value)} className="font-mono" placeholder="https://" /></Field>
            </div>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={!ok} onChange={(e) => setOk(!e.target.checked)} /> It failed</label>
            <div className="flex justify-end"><Button size="sm" onClick={record} disabled={pending || !version.trim() || (recording.stages.length > 0 && !stage)}>{ok ? <Check className="size-3.5" strokeWidth={2} /> : <Ban className="size-3.5" strokeWidth={2} />} Record</Button></div>
          </PanelBody>
        </Panel>
      )}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {state.targets.map((t) => <TargetBlock key={t.name} target={t} rows={state.deployments} canRecord={canRecord} onRecord={(target) => { setRecording(target); setStage(target.stages[0] ?? ""); }} />)}
      </div>
    </section>
  );
}
