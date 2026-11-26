"use client";

import { ExternalLink, RefreshCw, Settings2, ShieldCheck, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { SegmentedControl } from "@/components/ui/segmented";
import { Table, TBody, Td, Th, Tr } from "@/components/ui/table";
import type { Protection, RuleMode } from "@/lib/protection";
import { relativeTime } from "@/lib/time";
import { applyProtection, checkProtection, setProtection } from "./actions";
import { MODE_LABEL, MODE_TONE, type Setting, enforceOf, settingOf, summaryOf } from "./model";

const COLUMNS = [{ width: 30 }, { width: 22 }, { width: 48, hideBelow: "md" as const }];

export function ProtectionPanel({ projectId, appId, initial, canEdit }: { projectId: string; appId: string; initial: Protection; canEdit: boolean }) {
  const router = useRouter();
  const [protection, setState] = useState(initial);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const [busy, setBusy] = useState<"setting" | "apply" | "check" | null>(null);
  const setting = settingOf(protection);
  const summary = summaryOf(protection);
  const state = protection.state;
  const defaultLabel = `Organization default (${protection.organization_default ? "on" : "off"})`;

  const run = (kind: "setting" | "apply" | "check", action: () => Promise<{ ok: true; data: Protection } | { ok: false; error: string }>, done: (p: Protection) => string) => {
    setBusy(kind);
    setError(null);
    setNotice(null);
    start(async () => {
      const r = await action();
      setBusy(null);
      if (!r.ok) { setError(r.error); return; }
      setState(r.data);
      setNotice(done(r.data));
      router.refresh();
    });
  };

  const change = (next: Setting) => {
    if (next === setting || pending) return;
    run("setting", () => setProtection(projectId, appId, enforceOf(next)), (p) => (p.enforce ? (p.job_id ? "Saved — enforced. The rules are being applied on the code host in the background; Check host shows the result." : "Saved — enforced.") : "Saved — no longer enforced. The rules already on the host stay until removed there."));
  };

  return (
    <Panel>
      <PanelHeader
        title={<><ShieldCheck className="size-4 text-secondary" strokeWidth={1.75} /> Branch protection</>}
        description="Git-flow enforced by the code host itself: no direct push, force push or deletion on the protected branches, merges only through a pull request whose checks pass. Each rule below says whether the host enforces it, and who may still push."
        aside={<Badge tone={summary.tone}>{summary.label}</Badge>}
      />
      <PanelBody className="space-y-4 text-sm">
        <div className="space-y-1.5">
          <div className="text-xs text-secondary">Enforce on the code host</div>
          {canEdit ? (
            <SegmentedControl<Setting> label="Enforce branch protection" value={setting} onChange={change} options={[{ id: "default", label: "Default", hint: `organization: ${protection.organization_default ? "on" : "off"}` }, { id: "on", label: "On" }, { id: "off", label: "Off" }]} />
          ) : (
            <p>{setting === "default" ? defaultLabel : setting === "on" ? "On" : "Off"}</p>
          )}
          <p className="text-[13px] text-secondary">{summary.detail}</p>
          {busy === "setting" && <p className="text-[13px] text-secondary">Saving…</p>}
          {notice && <p role="status" className="text-[13px] text-foreground">{notice}</p>}
          {error && <p role="alert" className="text-[13px] text-status-bad">{error}</p>}
          {state?.error && state.fix && <FixLink label={state.fix.label} url={state.fix.url} />}
        </div>

        {state && (
          <dl className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div><dt className="text-xs text-secondary">Protected branches</dt><dd className="mt-0.5 font-mono">{state.branches.join(", ") || "—"}</dd></div>
            <div><dt className="text-xs text-secondary">Required checks</dt><dd className="mt-0.5 truncate font-mono" title={state.checks.join(", ")}>{state.checks.join(", ") || "none"}</dd></div>
            <div><dt className="text-xs text-secondary">May push</dt><dd className="mt-0.5 truncate">{state.bypass ?? "—"}</dd></div>
          </dl>
        )}

        {state && state.rules.length > 0 && (
          <div className="-mx-4 border-y border-border-subtle">
            <Table columns={COLUMNS} aria-label="Rules on the code host">
              <thead><tr><Th>Rule</Th><Th>State</Th><Th hideBelow="md">Detail</Th></tr></thead>
              <TBody>
                {state.rules.map((r) => (
                  <Tr key={r.rule}>
                    <Td className="truncate" title={r.label}>{r.label}</Td>
                    <Td><Badge tone={MODE_TONE[r.mode as RuleMode] ?? "neutral"}>{MODE_LABEL[r.mode as RuleMode] ?? r.mode}</Badge></Td>
                    <Td hideBelow="md" className="truncate text-secondary" title={r.detail}>{r.detail}</Td>
                  </Tr>
                ))}
              </TBody>
            </Table>
          </div>
        )}

        {state && state.drift.length > 0 && (
          <ul className="space-y-1 text-[13px]">
            {state.drift.map((d) => <li key={d} className="flex gap-2"><TriangleAlert className="mt-0.5 size-3.5 shrink-0" strokeWidth={1.75} aria-hidden />{d}</li>)}
            {state.changed_by && <li className="text-secondary">Last changed on the host by {state.changed_by}.</li>}
          </ul>
        )}

        <div className="flex flex-wrap items-center gap-3">
          {canEdit && <Button size="sm" loading={busy === "apply"} disabled={pending} onClick={() => run("apply", () => applyProtection(projectId, appId), (p) => (p.state?.error ? "Not applied — the reason is above." : "Applied on the code host."))}>Apply now</Button>}
          <Button size="sm" variant="outline" loading={busy === "check"} disabled={pending} onClick={() => run("check", () => checkProtection(projectId, appId), () => "Read from the code host just now.")}><RefreshCw className="size-3.5" strokeWidth={1.75} /> Check host</Button>
          <span className="text-[13px] text-secondary">
            {protection.checked_at ? `Checked ${relativeTime(protection.checked_at)}` : "Never checked"}
            {protection.applied_at ? ` · applied ${relativeTime(protection.applied_at)}` : ""}
          </span>
        </div>
      </PanelBody>
    </Panel>
  );
}

const FIX_CLASS = "inline-flex h-8 items-center gap-1.5 rounded-md border border-border px-3 text-[13px] text-foreground transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground";

function FixLink({ label, url }: { label: string; url: string }) {
  if (url.startsWith("/")) return <Link href={url} className={FIX_CLASS}><Settings2 className="size-3.5" strokeWidth={1.75} aria-hidden />{label}</Link>;
  return <a href={url} target="_blank" rel="noreferrer" className={FIX_CLASS}><ExternalLink className="size-3.5" strokeWidth={1.75} aria-hidden />{label}</a>;
}
