"use client";

import { Check, Cloud, ExternalLink, GitCommitHorizontal, Save, Upload, Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Hint } from "@/components/ui/hint";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { ActionField, ActionFields, ActionForm, ActionSummary } from "@/components/ui/action-form";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { useAction } from "@/lib/use-action";
import { RunAlert, summarize } from "@/features/deployments";
import { Field, Input } from "@/components/ui/input";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { cn } from "@/lib/utils";
import { planBranch } from "@/features/activity/actions";
import { addService, commitChanges, discardChanges, exportManifest, saveManifest, setCloudTarget } from "@/features/configuration/actions";
import type { AppView } from "@/features/projects";

type CloudOption = { name: string; description: string; source: string };
type ServiceOption = { name: string; providers: string[]; description: string; source: string };

export function ConfigurationPanels({ view, clouds, services }: { view: AppView; clouds: CloudOption[]; services: ServiceOption[] }) {
  return (
    <div className="space-y-4">
      {!view.can["app.configure"] && <div className="rounded-lg border border-border bg-surface px-4 py-3 text-[13px] text-secondary">Your role can view the configuration but not change it.</div>}
      {view.workingTree === "dirty" && view.can["app.configure"] && <CommitBar view={view} />}
      <DeployTargetPanel view={view} clouds={clouds} />
      <ServicesPanel view={view} services={services} />
      <ManifestPanel view={view} />
    </div>
  );
}


function CommitBar({ view }: { view: AppView }) {
  const router = useRouter();
  const onProtected = view.onProtectedBranch;
  const hasRemote = !!view.repositoryUrl;
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("chore(platform): update configuration");
  const [newBranch, setNewBranch] = useState(onProtected);
  const [kind, setKind] = useState("chore");
  const [code, setCode] = useState("");
  const [slug, setSlug] = useState("configuration");
  const [pullRequest, setPullRequest] = useState(hasRemote && onProtected);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<{ branch: string; url: string | null } | null>(null);
  const [discarding, setDiscarding] = useState(false);
  const [pending, start] = useTransition();

  const [plan, setPlan] = useState<{ branch: string; base: string } | null>(null);
  useEffect(() => {
    if (!newBranch) return;
    let live = true;
    const timer = setTimeout(() => { planBranch(view.registryId, kind, code, slug).then((r) => { if (live && r.ok) setPlan(r.data); }); }, 150);
    return () => { live = false; clearTimeout(timer); };
  }, [view.registryId, kind, code, slug, newBranch]);
  const branchName = plan?.branch ?? `${kind}/…`;
  const canSubmit = message.trim() && (!newBranch || code.trim());

  const submit = () => start(async () => {
    setError(null);
    const r = await commitChanges(view.projectId, view.appId, view.registryId, {
      message: message.trim(),
      push: true,
      branch: newBranch ? { kind, code: code.trim(), slug: slug.trim() } : null,
      pullRequest,
    });
    if (r.ok) {
      if (r.data.pull_request) {
        router.push(`/projects/${view.projectId}/apps/${view.appId}/activity?opened=${r.data.pull_request.number}`);
        return;
      }
      setDone({ branch: r.data.branch, url: null });
    } else setError(r.error);
  });

  const close = () => { if (pending) return; setOpen(false); setError(null); if (done) { setDone(null); router.refresh(); } };

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-foreground/60 bg-surface px-4 py-3 sm:flex-row sm:items-start">
      <div className="min-w-0 flex-1 text-sm">
        <div className="font-medium">Uncommitted changes on <span className="font-mono">{view.branch}</span></div>
        <div className="text-[13px] text-secondary">{onProtected ? "Protected branch: changes go to a new branch and a pull request." : "Configuration edits stay pending on the platform until you commit them; every commit is pushed."}</div>
        {view.changes.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {view.changes.slice(0, 12).map((f) => <span key={f} className="inline-flex h-5 items-center rounded border border-border bg-background px-1.5 font-mono text-[11px]">{f}</span>)}
            {view.changes.length > 12 && <span className="text-[11px] text-muted-foreground">+{view.changes.length - 12}</span>}
          </div>
        )}
      </div>
      <div className="flex shrink-0 gap-2">
        <Button variant="outline" onClick={() => setDiscarding(true)}>Discard</Button>
        <Button onClick={() => setOpen(true)}><GitCommitHorizontal className="size-4" strokeWidth={1.75} /> Commit changes</Button>
      </div>
      <ConfirmDialog
        open={discarding}
        onClose={() => setDiscarding(false)}
        title="Discard uncommitted changes?"
        description={`${view.changes.length} ${view.changes.length === 1 ? "file goes" : "files go"} back to the last commit; untracked files are deleted. This cannot be undone.`}
        confirmLabel="Discard changes"
        danger
        pending={pending}
        onConfirm={() => start(async () => { const r = await discardChanges(view.projectId, view.registryId); setDiscarding(false); if (r.ok) router.refresh(); else setError(r.error); })}
      />
      <Dialog
        open={open}
        onClose={close}
        title={done ? "Changes committed" : "Commit changes"}
        description={done ? undefined : <>Conventional Commits. {onProtected && <>Direct commits on <span className="font-mono">{view.branch}</span> are not allowed.</>}</>}
        footer={done ? <Button onClick={close}>Done</Button> : <><Button variant="ghost" onClick={close} disabled={pending}>Cancel</Button><Button disabled={pending || !canSubmit} onClick={submit}>{pending ? "Working…" : pullRequest ? "Commit and open PR" : "Commit"}</Button></>}
      >
        {done ? (
          <div className="space-y-2 text-sm">
            <div>Committed on <span className="font-mono">{done.branch}</span> and pushed.</div>
            {done.url && <a href={done.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 underline underline-offset-4">Open pull request <ExternalLink className="size-3.5" strokeWidth={1.75} /></a>}
          </div>
        ) : (
          <div className="space-y-3">
            <Field label="Message"><Input value={message} onChange={(e) => setMessage(e.target.value)} className="font-mono" autoFocus /></Field>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={newBranch} onChange={(e) => { setNewBranch(e.target.checked); if (!e.target.checked) setPullRequest(false); }} disabled={onProtected} /> Commit on a new branch{onProtected && <span className="text-xs text-secondary">required here</span>}</label>
            {newBranch && (
              <div className="space-y-2 rounded-md border border-border p-3">
                <div className="flex flex-wrap gap-1">
                  {view.branchKinds.map((k) => <button key={k} type="button" onClick={() => setKind(k)} aria-pressed={kind === k} className={cn("h-8 rounded-md border px-2.5 font-mono text-xs", kind === k ? "border-foreground" : "border-border text-secondary hover:border-border-hover")}>{k}</button>)}
                </div>
                <div className="grid gap-2 sm:grid-cols-2">
                  <Field label="Code"><Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="42" className="font-mono" /></Field>
                  <Field label="Slug"><Input value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="optional" className="font-mono" /></Field>
                </div>
                <div className="text-xs text-secondary">Branch <span className="font-mono text-foreground">{branchName}</span></div>
              </div>
            )}
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={pullRequest} onChange={(e) => setPullRequest(e.target.checked)} disabled={!hasRemote || (!newBranch && onProtected)} /> Open a pull request</label>
            <p className="text-xs text-muted-foreground">The commit is pushed right away: the platform keeps nothing that is not on the code host.</p>
            {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
          </div>
        )}
      </Dialog>
    </div>
  );
}

function DeployTargetPanel({ view, clouds }: { view: AppView; clouds: CloudOption[] }) {
  const router = useRouter();
  const current = typeof view.deploy.target === "string" ? String(view.deploy.target) : null;
  const [name, setName] = useState(current ?? clouds[0]?.name ?? "");
  const chosen = clouds.find((c) => c.name === name) ?? null;
  const can = view.can["app.configure"];
  const action = useAction<never, { target: string }>({
    run: () => setCloudTarget(view.projectId, view.registryId, chosen!.name, chosen!.source),
    onDone: () => router.refresh(),
  });
  const blocker = !can ? "Your role cannot change the configuration." : clouds.length === 0 ? `No overlay supports ${view.type ?? "this type"} / ${view.language ?? "this language"}.` : chosen && chosen.name === current ? "Already the target." : null;

  return (
    <ActionForm
      title="Deploy target"
      aside={current ? <Badge className="font-mono">{current}</Badge> : <Badge>Not configured</Badge>}
      primary={{ label: current && chosen && chosen.name !== current ? "Replace target" : "Apply overlay", icon: Cloud, onClick: action.confirm, disabled: !!blocker || !chosen, busy: action.busy, busyLabel: "Applying…" }}
      blocker={action.error ? null : blocker}
      summary={[{ label: "Current", value: current ?? "—" }, { label: "Chosen", value: chosen?.name ?? "—" }, { label: "Source", value: chosen?.source ?? "—" }, { label: "Result", value: "pending changes" }]}
      alerts={action.error ? <RunAlert tone="danger" title="Could not apply" summary={summarize(action.error)} log={action.error} /> : null}
      dialogs={
        <ConfirmDialog open={action.step === "confirming"} onClose={action.cancel} title={`Set deploy target to ${chosen?.name}?`} confirmLabel="Apply overlay" pending={action.busy} onConfirm={action.execute}>
          <ActionSummary items={[{ label: "Target", value: chosen?.name ?? "—" }, { label: "Replaces", value: current ?? "nothing" }, { label: "Source", value: chosen?.source ?? "—" }, { label: "Then", value: "commit the changes" }]} />
          <p className="mt-4 text-sm text-secondary">Adds the cloud overlay&apos;s files as pending changes and records <span className="font-mono">[deploy] target</span> in <span className="font-mono">platform.toml</span>. Nothing reaches the repository until you commit.</p>
        </ConfirmDialog>
      }
    >
      <ActionFields>
        <ActionField label="Cloud" hint={<Hint text="The overlay brings the deploy template, a workflow, a health route and an adapter per language." />}>
          <Select size="lg" mono icon={<Cloud className="size-4" strokeWidth={1.75} />} value={name} onChange={(v) => { setName(v); action.clearOutcome(); }} disabled={!can || clouds.length === 0} options={clouds.map((c) => ({ value: c.name, label: c.name, hint: c.name === current ? "current" : c.source !== "official" ? c.source : undefined }))} />
        </ActionField>
        <ActionField label="About">
          <div className="flex h-[42px] items-center truncate rounded-[7px] border border-dashed border-border px-3 text-sm text-secondary" title={chosen?.description}>{chosen?.description ?? "Pick a cloud"}</div>
        </ActionField>
      </ActionFields>
    </ActionForm>
  );
}

function ServicesPanel({ view, services }: { view: AppView; services: ServiceOption[] }) {
  const router = useRouter();
  const [name, setName] = useState(services[0]?.name ?? "");
  const [provider, setProvider] = useState<string>(services[0]?.providers[0] ?? "");
  const chosen = services.find((s) => s.name === name);
  const can = view.can["app.configure"];
  const action = useAction<never, { name: string }>({
    run: () => addService(view.projectId, view.registryId, name, provider || null, chosen?.source ?? null),
    onDone: () => router.refresh(),
  });
  const blocker = !can ? "Your role cannot change the configuration." : services.length === 0 ? "The templates matrix offers no service." : view.services.includes(name) ? `${name} is already added.` : null;

  return (
    <ActionForm
      title="Services"
      aside={<Badge>{view.services.length} {view.services.length === 1 ? "service" : "services"}</Badge>}
      primary={{ label: "Add service", icon: Plus, onClick: action.confirm, disabled: !!blocker || !name, busy: action.busy, busyLabel: "Adding…" }}
      blocker={action.error ? null : blocker}
      summary={[{ label: "Installed", value: view.services.join(", ") || "none" }, { label: "Chosen", value: name || "—" }, { label: "Provider", value: provider || "—" }, { label: "Result", value: "pending changes" }]}
      alerts={action.error ? <RunAlert tone="danger" title="Could not add" summary={summarize(action.error)} log={action.error} /> : null}
      dialogs={
        <ConfirmDialog open={action.step === "confirming"} onClose={action.cancel} title={`Add ${name}?`} confirmLabel="Add service" pending={action.busy} onConfirm={action.execute}>
          <ActionSummary items={[{ label: "Service", value: name }, { label: "Provider", value: provider || "—" }, { label: "Files", value: `services/${name}/` }, { label: "Then", value: "commit the changes" }]} />
          <p className="mt-4 text-sm text-secondary">Adds <span className="font-mono">services/{name}/</span> with up and link scripts as pending changes and records it under <span className="font-mono">[services]</span>.</p>
        </ConfirmDialog>
      }
    >
      <ActionFields>
        <ActionField label="Service" hint={<Hint text="Databases, caches and storage come as services/<name>/ with up and link scripts." />}>
          <Select size="lg" mono value={name} onChange={(v) => { setName(v); setProvider(services.find((s) => s.name === v)?.providers[0] ?? ""); action.clearOutcome(); }} disabled={!can || services.length === 0} options={services.map((s) => ({ value: s.name, label: s.name, hint: view.services.includes(s.name) ? "installed" : s.source !== "official" ? s.source : undefined }))} />
        </ActionField>
        <ActionField label="Provider">
          {chosen && chosen.providers.length > 0 ? (
            <Select size="lg" mono value={provider} onChange={(v) => { setProvider(v); action.clearOutcome(); }} disabled={!can} options={chosen.providers.map((p) => ({ value: p, label: p }))} />
          ) : (
            <div className="flex h-[42px] items-center rounded-[7px] border border-dashed border-border px-3 font-mono text-sm text-muted-foreground">{chosen ? "single provider" : "—"}</div>
          )}
        </ActionField>
      </ActionFields>
    </ActionForm>
  );
}

function ManifestPanel({ view }: { view: AppView }) {
  const router = useRouter();
  const [content, setContent] = useState(view.manifest);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [pending, start] = useTransition();
  const dirty = content !== view.manifest;
  const canEdit = view.can["app.configure"];

  return (
    <Panel>
      <PanelHeader
        title="Configuration"
        aside={
          <div className="flex items-center gap-2">
            <Hint text="Stored on the platform and used by every release and deploy. platform.toml in the repository is a mirror: export it when the CLI, git hooks or CI need the same values."><Badge tone={view.manifestMirrored ? "neutral" : "inverse"}>{view.manifestMirrored ? "Repository in sync" : "Repository differs"}</Badge></Hint>
            {canEdit && !view.manifestMirrored && <Button size="sm" variant="outline" disabled={pending || dirty} onClick={() => start(async () => { setError(null); const r = await exportManifest(view.projectId, view.registryId); if (r.ok) router.refresh(); else setError(r.error); })}><Upload className="size-4" strokeWidth={1.75} /> Export to repository</Button>}
            <Button size="sm" disabled={pending || !dirty || !canEdit} onClick={() => start(async () => { setError(null); const r = await saveManifest(view.projectId, view.registryId, content); if (r.ok) { setSaved(true); setTimeout(() => setSaved(false), 1500); router.refresh(); } else setError(r.error); })}>{saved ? <Check className="size-4" strokeWidth={2.5} /> : <Save className="size-4" strokeWidth={1.75} />} {pending ? "Saving…" : saved ? "Saved" : "Save"}</Button>
          </div>
        }
      />
      <PanelBody className="space-y-2">
        <textarea value={content} onChange={(e) => setContent(e.target.value)} readOnly={!canEdit} spellCheck={false} rows={Math.max(12, content.split("\n").length + 1)} className="w-full rounded-md px-3 py-2 font-mono text-xs leading-5" />
        {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
        <p className="text-xs text-muted-foreground">TOML, validated on save. Saving changes the platform&apos;s copy at once — no commit needed. <span className="font-mono">Export to repository</span> writes platform.toml into the clone as a pending change to commit.</p>
      </PanelBody>
    </Panel>
  );
}
