"use client";

import { Play, Check } from "lucide-react";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { SegmentedControl } from "@/components/ui/segmented";
import { Select } from "@/components/ui/select";
import { call } from "@/lib/call";
import type { AccessPlan, ServiceAuditRow } from "@/lib/v1";
import { type Operation, runOperation } from "./actions";
import { canApply, summarizePlan, summaryText } from "./plan";
import { PlanView } from "./plan-view";

type Kind = Operation["kind"];

const KINDS: { id: Kind; label: string }[] = [
  { id: "sync", label: "Sync" },
  { id: "grant", label: "Grant" },
  { id: "revoke", label: "Revoke" },
  { id: "offboard", label: "Offboard" },
];

const INTRO: Record<Kind, string> = {
  sync: "Imports a service the first time, then adds, changes and removes access to close the drift.",
  grant: "One grant to one person, recorded in the mapping. Only that person's account is touched.",
  revoke: "Takes one grant away from one person; says when their role or a team still grants it.",
  offboard: "Every grant of every account linked to the person, and their mapping entries.",
};

export function AccessOperations({ services }: { services: ServiceAuditRow[] }) {
  const [kind, setKind] = useState<Kind>("sync");
  const [service, setService] = useState("");
  const [person, setPerson] = useState("");
  const [resource, setResource] = useState("");
  const [level, setLevel] = useState("");
  const [account, setAccount] = useState("");
  const [reimport, setReimport] = useState(false);
  const [removeFromPlatform, setRemoveFromPlatform] = useState(false);
  const [plan, setPlan] = useState<AccessPlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [pending, start] = useTransition();

  const options = services.map((s) => ({ value: s.service, label: s.service }));
  const chosen = services.find((s) => s.service === service);
  const levels = Object.entries(chosen?.levels ?? {});
  const unimported = kind === "sync" && (service ? services.filter((s) => s.service === service) : services).some((s) => s.ok && !s.imported);

  const edit = <T,>(set: (v: T) => void) => (v: T) => {
    set(v);
    setPlan(null);
    setError(null);
  };

  const operation = (): Operation => {
    if (kind === "sync") return { kind, service: service || undefined, reimport };
    if (kind === "grant") return { kind, person, service, resource, level, account: account || undefined };
    if (kind === "revoke") return { kind, person, service, resource };
    return { kind, person, removeFromPlatform };
  };

  const run = (apply: boolean) =>
    start(async () => {
      setError(null);
      const r = await call(() => runOperation(operation(), apply), (e) => ({ ok: false as const, error: e }));
      setConfirming(false);
      if (r.ok) setPlan(r.data);
      else {
        setError(r.error);
        if (!apply) setPlan(null);
      }
    });

  const ready = kind === "sync" || (person.trim() !== "" && (kind === "offboard" || (service !== "" && resource.trim() !== "" && (kind === "revoke" || level.trim() !== ""))));
  const summary = plan ? summarizePlan(plan) : null;

  return (
    <Panel>
      <PanelHeader title="Change access" description="Every change is a dry run first: the plan shows what would happen, and nothing changes until you apply it." />
      <div className="space-y-4 p-4">
        <SegmentedControl label="Operation" value={kind} options={KINDS} onChange={(k) => { setKind(k); setPlan(null); setError(null); }} />
        <p className="text-[13px] text-secondary">{INTRO[kind]}</p>
        <form
          className="grid gap-3 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (ready && !pending) run(false);
          }}
        >
          {kind !== "sync" && <Field label="Person (email)"><Input type="email" value={person} onChange={(e) => edit(setPerson)(e.target.value)} placeholder="ada@example.com" autoComplete="off" /></Field>}
          {kind !== "offboard" && (
            <Field label={kind === "sync" ? "Service (empty for all)" : "Service"}>
              <Select value={service} options={kind === "sync" ? [{ value: "", label: "All services" }, ...options] : options} onChange={edit(setService)} placeholder="Choose a service" aria-label="Service" />
            </Field>
          )}
          {(kind === "grant" || kind === "revoke") && <Field label="Resource" hint={levels.length ? `Kinds: ${levels.map(([k]) => k).join(", ")}` : undefined}><Input value={resource} onChange={(e) => edit(setResource)(e.target.value)} placeholder="repo/api" autoComplete="off" /></Field>}
          {kind === "grant" && <Field label="Level" hint={levels.length ? levels.map(([k, l]) => `${k}: ${l.join(" < ")}`).join(" · ") : undefined}><Input value={level} onChange={(e) => edit(setLevel)(e.target.value)} placeholder="push" autoComplete="off" /></Field>}
          {kind === "grant" && <Field label="Account (optional)" hint="Only when it is not the person's email."><Input value={account} onChange={(e) => edit(setAccount)(e.target.value)} autoComplete="off" /></Field>}
          {kind === "sync" && (
            <label className="flex items-center gap-2 text-sm sm:col-span-2">
              <input type="checkbox" checked={reimport} onChange={(e) => edit(setReimport)(e.target.checked)} />
              Import again: record what the service holds today in the mapping, replacing the stored import
            </label>
          )}
          {kind === "offboard" && (
            <label className="flex items-center gap-2 text-sm sm:col-span-2">
              <input type="checkbox" checked={removeFromPlatform} onChange={(e) => edit(setRemoveFromPlatform)(e.target.checked)} />
              Also remove them from the platform organization
            </label>
          )}
          <div className="sm:col-span-2">
            <Button type="submit" variant="outline" loading={pending && !confirming} disabled={!ready || pending}>
              <Play className="size-3.5" strokeWidth={2} /> {kind === "sync" && unimported ? "Preview import" : "Dry run"}
            </Button>
          </div>
        </form>
        {unimported && !plan && <p className="text-[13px] text-secondary">A service that is not imported yet is imported by the first sync; nothing changes on it.</p>}
        {error && <div className="rounded-md border border-status-bad/30 bg-status-bad/5 px-3 py-2 text-[13px] text-status-bad">{error}</div>}
        {plan && (
          <div className="space-y-3">
            <PlanView plan={plan} />
            {canApply(plan) && (
              <Button onClick={() => setConfirming(true)} disabled={pending}>
                <Check className="size-3.5" strokeWidth={2} /> {plan.bootstrap && summary?.total === 0 ? "Apply import" : "Apply"}
              </Button>
            )}
          </div>
        )}
      </div>
      <ConfirmDialog
        open={confirming}
        onClose={() => setConfirming(false)}
        onConfirm={() => run(true)}
        title={kind === "offboard" ? "Offboard this person?" : "Apply this plan?"}
        description={plan ? `${summaryText(summary ?? summarizePlan(plan))}.${plan.bootstrap ? " Imports what the service holds today and changes nothing on it." : ""}` : undefined}
        confirmLabel="Apply"
        danger={kind === "offboard" || kind === "revoke" || (summary?.remove ?? 0) > 0}
        pending={pending}
      />
    </Panel>
  );
}
