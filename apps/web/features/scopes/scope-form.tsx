"use client";

import { Cloud, Save, Target } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { ActionField, ActionFields, ActionForm } from "@/components/ui/action-form";
import { Hint } from "@/components/ui/hint";
import { Input } from "@/components/ui/input";
import { SegmentedControl } from "@/components/ui/segmented";
import { Select } from "@/components/ui/select";
import { ACCEPTS, CRITICALITY, type Criticality, type Scope, type Scopes } from "@/lib/scope-kinds";
import { RunAlert, summarize } from "@/features/deployments";
import { createScope, updateScope } from "./actions";

const SLUG = /^[a-z0-9][a-z0-9-]{0,62}$/;

export function ScopeForm({ projectId, appId, base, vocabulary, targets, scope = null, canEdit }: {
  projectId: string;
  appId: string;
  base: string;
  vocabulary: Pick<Scopes, "kinds" | "criticalities" | "executors">;
  targets: { name: string; description: string }[];
  scope?: Scope | null;
  canEdit: boolean;
}) {
  const router = useRouter();
  const editing = scope !== null;
  const [name, setName] = useState(scope?.name ?? "");
  const [kind, setKind] = useState(scope?.kind ?? "web");
  const [criticality, setCriticality] = useState<Criticality>((scope?.criticality as Criticality) ?? "low");
  const [target, setTarget] = useState(scope?.target ?? targets[0]?.name ?? "");
  const [runBy, setRunBy] = useState(scope?.run_by ?? "platform");
  const [url, setUrl] = useState(scope?.url ?? "");
  const [region, setRegion] = useState(String(scope?.options?.region ?? ""));
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  const validName = SLUG.test(name.trim());
  const blocker = !canEdit ? "Your role cannot change the configuration." : !validName ? "Name: lowercase letters, digits and hyphens." : null;
  const meta = CRITICALITY[criticality];

  const save = () => start(async () => {
    setError(null);
    const body = { name: name.trim(), kind, criticality, target: target || null, run_by: runBy, url: url.trim() || null, options: region.trim() ? { region: region.trim() } : {} };
    const r = editing ? await updateScope(projectId, appId, scope!.name, body) : await createScope(projectId, appId, body);
    if (!r.ok) { setError(r.error); return; }
    router.push(`${base}/scopes`);
    router.refresh();
  });

  return (
    <ActionForm
      title={editing ? `Edit scope ${scope!.name}` : "New scope"}
      primary={{ label: editing ? "Save scope" : "Create scope", icon: editing ? Save : Target, onClick: save, disabled: !!blocker, busy: pending, busyLabel: "Saving…" }}
      blocker={error ? null : blocker}
      summary={[{ label: "Name", value: name || "—" }, { label: "Kind", value: kind }, { label: "Criticality", value: meta.label }, { label: "Accepts", value: ACCEPTS[criticality].join(", ") }, { label: "Target", value: target || "—" }]}
      alerts={error ? <RunAlert tone="danger" title="Could not save the scope" summary={summarize(error)} log={error} /> : undefined}
    >
      <ActionFields>
        <ActionField label="Name" hint={<Hint text="Unique within the app: dev, staging, prod-eu, nightly-jobs. The plugin sees it as the stage — aws/lambda names the stack <prefix>-<name>." />}>
          <Input className="h-[42px] rounded-[7px] font-mono" value={name} onChange={(e) => setName(e.target.value)} placeholder="staging" disabled={editing || !canEdit} autoFocus={!editing} />
        </ActionField>
        <ActionField label="Kind" hint={<Hint text="What runs there: web answers HTTP, job runs to completion, worker consumes a queue, static is files behind a CDN, library is published to a registry." />}>
          <Select size="lg" mono value={kind} onChange={setKind} options={vocabulary.kinds.map((k) => ({ value: k, label: k }))} disabled={!canEdit} />
        </ActionField>
        <ActionField label="Criticality" hint={<Hint text={meta.hint} />}>
          <SegmentedControl label="Criticality" value={criticality} onChange={setCriticality} options={vocabulary.criticalities.map((c) => ({ id: c as Criticality, label: CRITICALITY[c as Criticality]?.label ?? c }))} />
        </ActionField>
        <ActionField label="Target" hint={<Hint text="The deploy target that puts a release there; the plugin options (region…) go with it." />}>
          <Select size="lg" mono icon={<Cloud className="size-4" strokeWidth={1.75} />} value={target} onChange={setTarget} options={[{ value: "", label: "— app's configured target —" }, ...targets.map((t) => ({ value: t.name, label: t.name, hint: t.description }))]} disabled={!canEdit} />
        </ActionField>
        <ActionField label="Region" hint={<Hint text="Passed to the target as its region option; leave empty to use the target's default." />}>
          <Input className="h-[42px] rounded-[7px] font-mono" value={region} onChange={(e) => setRegion(e.target.value)} placeholder="us-east-1" disabled={!canEdit} />
        </ActionField>
        <ActionField label="Run by" hint={<Hint text="Who executes deploys to this scope: the platform, or a pipeline the platform observes." />}>
          <Select size="lg" mono value={runBy} onChange={setRunBy} options={vocabulary.executors.map((e) => ({ value: e, label: e }))} disabled={!canEdit} />
        </ActionField>
        <ActionField label="URL" hint={<Hint text="Where the scope can be seen, when it has an address." />}>
          <Input className="h-[42px] rounded-[7px] font-mono" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://" disabled={!canEdit} />
        </ActionField>
      </ActionFields>
    </ActionForm>
  );
}
