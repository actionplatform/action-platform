"use client";

import { Check, Link2, RefreshCw, Settings2, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { Select } from "@/components/ui/select";
import { CI_HOST_KINDS, CI_LABELS, type CiHost, type CiState } from "@/lib/ci";
import { call } from "@/lib/call";
import { linkCi, syncCi } from "./actions";
import { RunBadge } from "./run-badge";
import { RunsTable } from "./runs-table";

type Props = { projectId: string; appId: string; state: CiState; hosts: CiHost[]; sourceKind: string | null; defaultBranch: string; canConfigure: boolean; canSync: boolean };

const EMBEDDED = "__embedded__";

export function CiPanel({ projectId, appId, state: initial, hosts, sourceKind, defaultBranch, canConfigure, canSync }: Props) {
  const router = useRouter();
  const [state, setState] = useState(initial);
  const [editing, setEditing] = useState(false);
  const [hostId, setHostId] = useState(initial.link.ciHostId ?? EMBEDDED);
  const [job, setJob] = useState(initial.link.job);
  const [error, setError] = useState<string | null>(initial.error);
  const [status, setStatus] = useState<"idle" | "syncing" | "success" | "error">("idle");
  const [pending, start] = useTransition();

  const connected = state.link.kind !== "none";
  const host = hosts.find((h) => h.id === state.link.ciHostId) ?? null;
  const meta = CI_HOST_KINDS.find((k) => k.id === (hosts.find((h) => h.id === hostId)?.kind ?? "")) ?? null;
  const embeddedLabel = sourceKind === "github" ? "GitHub Actions" : null;
  const onMain = state.runs.filter((r) => r.branch === defaultBranch);
  const last = onMain[0] ?? state.runs[0] ?? null;
  const finished = state.runs.filter((r) => ["success", "failure", "unstable", "aborted"].includes(r.status)).slice(0, 20);
  const rate = finished.length ? Math.round((finished.filter((r) => r.status === "success").length / finished.length) * 100) : null;

  const save = () =>
    start(async () => {
      setError(null);
      const r = await call(() => linkCi(projectId, appId, hostId === EMBEDDED ? null : hostId, job), (e) => ({ ok: false as const, error: e }), "Reload the page to see the current state.");
      if (!r.ok) { setError(r.error); return; }
      setEditing(false);
      router.refresh();
    });

  const sync = () =>
    start(async () => {
      setStatus("syncing");
      const r = await call(() => syncCi(projectId, appId), (e) => ({ ok: false as const, error: e }), "Reload the page to see the current state.");
      if (!r.ok) { setStatus("error"); setError(r.error); return; }
      setState(r.data);
      setError(r.data.error);
      setStatus(r.data.error ? "error" : "success");
      setTimeout(() => setStatus("idle"), 2500);
    });

  const syncButton = canSync && connected ? (
    <Button size="sm" variant="outline" onClick={sync} disabled={pending}>
      <RefreshCw className={`size-3.5 ${status === "syncing" ? "animate-spin" : ""}`} strokeWidth={2} /> {status === "syncing" ? "Syncing…" : status === "success" ? "Synced" : "Sync"}
    </Button>
  ) : null;

  const form = (
    <PanelBody className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="CI" hint={hosts.length === 0 && !embeddedLabel ? "Add a CI server under Settings first." : undefined}>
          <Select
            value={hostId}
            onChange={setHostId}
            aria-label="CI"
            options={[
              { value: EMBEDDED, label: embeddedLabel ?? "None", hint: embeddedLabel ? "Uses the source host's token" : "The source host has no CI of its own" },
              ...hosts.map((h) => ({ value: h.id, label: h.name, hint: `${CI_LABELS[h.kind] ?? h.kind} · ${h.baseUrl}` })),
            ]}
          />
        </Field>
        <Field label="Job" hint={meta?.jobHint ?? (hostId === EMBEDDED && embeddedLabel ? "A workflow file such as ci.yml, or empty for every workflow." : undefined)}>
          <Input value={job} onChange={(e) => setJob(e.target.value)} className="font-mono" placeholder={meta ? "team/app/main" : "ci.yml"} disabled={hostId === EMBEDDED && !embeddedLabel} />
        </Field>
      </div>
      {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
      <div className="flex justify-end gap-2">
        {connected && <Button size="sm" variant="ghost" onClick={() => { setEditing(false); setError(null); }} disabled={pending}><X className="size-3.5" strokeWidth={2} /> Cancel</Button>}
        <Button size="sm" onClick={save} disabled={pending || (hostId === EMBEDDED && !embeddedLabel)}><Check className="size-3.5" strokeWidth={2} /> {pending ? "Saving…" : "Save"}</Button>
      </div>
    </PanelBody>
  );

  if (!connected || editing) {
    return (
      <Panel>
        <PanelHeader title={connected ? "CI" : "Connect a CI"} />
        {!connected && !editing && (
          <div className="flex flex-col items-center px-4 pt-10 text-center">
            <Link2 className="size-5 text-secondary" strokeWidth={1.5} />
            <div className="mt-3 text-sm font-medium">No CI connected</div>
            <div className="max-w-md text-[13px] text-secondary">{canConfigure ? "Pick where this app's builds run and which job to read. Runs are imported into the platform; nothing is triggered." : "Someone with configure access can connect one."}</div>
          </div>
        )}
        {canConfigure && form}
      </Panel>
    );
  }

  return (
    <div className="space-y-4">
      <Panel>
        <PanelHeader
          title="CI"
          aside={
            <div className="flex items-center gap-2">
              {syncButton}
              {canConfigure && <Button size="sm" variant="ghost" onClick={() => setEditing(true)} aria-label="Change CI"><Settings2 className="size-3.5" strokeWidth={2} /></Button>}
            </div>
          }
        />
        <dl className="grid grid-cols-2 gap-4 px-4 py-4 text-sm sm:grid-cols-4">
          <div><dt className="text-xs text-secondary">Runner</dt><dd className="mt-0.5 font-medium">{CI_LABELS[state.link.kind] ?? state.link.kind}{host && <span className="block truncate font-mono text-xs text-secondary">{host.baseUrl}</span>}</dd></div>
          <div><dt className="text-xs text-secondary">Job</dt><dd className="mt-0.5 truncate font-mono">{state.link.job || (state.link.kind === "github_actions" ? "all workflows" : "—")}</dd></div>
          <div><dt className="text-xs text-secondary">Last on {defaultBranch}</dt><dd className="mt-0.5">{last ? <RunBadge status={last.status} /> : <span className="text-secondary">—</span>}</dd></div>
          <div><dt className="text-xs text-secondary">Pass rate</dt><dd className="mt-0.5 font-medium">{rate === null ? <span className="text-secondary">—</span> : `${rate}%`}{rate !== null && <span className="block text-xs text-secondary">last {finished.length}</span>}</dd></div>
        </dl>
        {error && <div className="border-t border-border-subtle px-4 py-2 text-[13px] text-secondary">{error}</div>}
      </Panel>
      <RunsTable runs={state.runs} source={state.link.kind} />
    </div>
  );
}
