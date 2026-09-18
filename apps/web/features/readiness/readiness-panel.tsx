"use client";

import { AlertTriangle, CheckCircle2, Loader2, RefreshCw, ShieldCheck, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, PanelHeader } from "@/components/ui/panel";
import type { ReadinessCheck, ReadinessRow } from "@/lib/releases";
import { relativeTime } from "@/lib/time";
import { checkReadiness, readiness as fetchReadiness } from "./actions";

const VERDICT: Record<string, { tone: "success" | "danger" | "neutral"; label: string }> = {
  ok: { tone: "success", label: "Deployable" },
  blocked: { tone: "danger", label: "Blocked" },
  pending: { tone: "neutral", label: "Checking…" },
};

function Mark({ check }: { check: ReadinessCheck }) {
  if (check.ok) return <CheckCircle2 className="size-4 shrink-0 text-status-ok" strokeWidth={1.75} aria-label="ok" />;
  if (check.severity === "warning") return <AlertTriangle className="size-4 shrink-0 text-status-warn" strokeWidth={1.75} aria-label="warning" />;
  return <XCircle className="size-4 shrink-0 text-status-bad" strokeWidth={1.75} aria-label="failed" />;
}

function Stage({ row }: { row: ReadinessRow }) {
  const v = VERDICT[row.verdict] ?? VERDICT.pending;
  const checks = [...row.checks].sort((a, b) => Number(a.ok) - Number(b.ok));
  return (
    <div className="rounded-lg border border-border bg-surface">
      <div className="flex min-h-11 flex-wrap items-center gap-2 border-b border-border-subtle px-4 py-2">
        <span className="font-mono text-sm font-semibold">{row.stage}</span>
        <Badge tone={v.tone} className="h-5 px-2 text-[11px]">{row.verdict === "pending" && <Loader2 className="mr-1 size-3 animate-spin" aria-hidden="true" />}{v.label}</Badge>
        <span className="ml-auto text-xs text-secondary">{row.checked_at ? `checked ${relativeTime(row.checked_at)}` : row.status}</span>
      </div>
      {checks.length === 0 ? (
        <div className="px-4 py-3 text-[13px] text-secondary">{row.verdict === "pending" ? "The worker is running the checks." : "Nothing was checked."}</div>
      ) : (
        <ul className="divide-y divide-border-subtle">
          {checks.map((c, i) => (
            <li key={`${c.id}-${c.target ?? ""}-${i}`} className="flex flex-col gap-1 px-4 py-2 text-sm sm:flex-row sm:items-start sm:gap-3">
              <Mark check={c} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-medium">{c.id}</span>
                  {c.target && <span className="font-mono text-[11px] text-secondary">{c.target}</span>}
                  <Badge className="h-4 px-1.5 text-[10px]">{c.level}</Badge>
                </div>
                <div className="break-words text-[13px] text-secondary">{c.detail}</div>
                {!c.ok && c.fix && <div className="mt-0.5 text-[13px]"><span className="text-secondary">Fix:</span> {c.fix}</div>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function ReadinessPanel({ projectId, appId, tag, initial, canCheck }: { projectId: string; appId: string; tag: string; initial: ReadinessRow[]; canCheck: boolean }) {
  const [rows, setRows] = useState<ReadinessRow[]>(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pending = rows.some((r) => r.verdict === "pending");

  useEffect(() => {
    if (!pending) return;
    const timer = setInterval(async () => {
      const r = await fetchReadiness(projectId, appId, tag);
      if (r.ok) setRows(r.data);
    }, 3000);
    return () => clearInterval(timer);
  }, [pending, projectId, appId, tag]);

  const recheck = async () => {
    if (busy) return;
    setBusy(true);
    setError(null);
    const r = await checkReadiness(projectId, appId, tag);
    setBusy(false);
    if (!r.ok) { setError(r.error); return; }
    setRows(r.data.readiness);
  };

  return (
    <Panel>
      <PanelHeader
        title={<><ShieldCheck className="size-4 text-secondary" strokeWidth={1.75} /> Readiness</>}
        description="Whether this release can reach each stage: configuration, manifests, credentials, permissions and the destination's state. Nothing is built or changed."
        aside={canCheck && <Button size="sm" variant="outline" onClick={recheck} loading={busy} disabled={pending}><RefreshCw className="size-3.5" strokeWidth={1.75} /> Re-check</Button>}
      />
      <div className="space-y-3 p-4">
        {error && <div className="rounded-md border border-status-bad/30 bg-status-bad/10 px-3 py-2 text-sm text-status-bad">{error}</div>}
        {rows.length === 0 ? (
          <div className="text-[13px] text-secondary">Not checked yet.{canCheck && " Re-check runs the checks for dev and prod."}</div>
        ) : rows.map((r) => <Stage key={r.stage} row={r} />)}
      </div>
    </Panel>
  );
}
