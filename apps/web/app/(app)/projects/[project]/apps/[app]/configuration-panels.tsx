"use client";

import { Check, Cloud, ExternalLink, GitCommitHorizontal, Save } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { CheckIndicator } from "@/components/ui/check-indicator";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { cn } from "@/lib/utils";
import { addService, commitChanges, saveManifest, setCloudTarget } from "../actions";
import type { AppView } from "./model";

type CloudOption = { name: string; description: string };
type ServiceOption = { name: string; providers: string[]; description: string };

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

const KINDS = ["chore", "feature", "bugfix", "docs", "ci", "refactor"];
const PROTECTED = ["main", "master", "develop"];

function slugify(text: string) {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

function CommitBar({ view }: { view: AppView }) {
  const router = useRouter();
  const onProtected = PROTECTED.includes(view.branch);
  const hasRemote = !!view.repositoryUrl;
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("chore(platform): update configuration");
  const [newBranch, setNewBranch] = useState(onProtected);
  const [kind, setKind] = useState("chore");
  const [code, setCode] = useState("");
  const [slug, setSlug] = useState("configuration");
  const [push, setPush] = useState(hasRemote);
  const [pullRequest, setPullRequest] = useState(hasRemote && onProtected);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<{ branch: string; url: string | null } | null>(null);
  const [pending, start] = useTransition();

  const branchName = `${kind}/${code.trim() || "<code>"}${slugify(slug) ? `-${slugify(slug)}` : ""}`;
  const canSubmit = message.trim() && (!newBranch || code.trim());

  const submit = () => start(async () => {
    setError(null);
    const r = await commitChanges(view.projectId, view.appId, view.registryId, {
      message: message.trim(),
      push: push || pullRequest,
      branch: newBranch ? { kind, code: code.trim(), slug: slugify(slug) } : null,
      pullRequest,
    });
    if (r.ok) {
      setDone({ branch: r.data.branch, url: r.data.pull_request?.url ?? null });
      router.refresh();
    } else setError(r.error);
  });

  const close = () => { if (pending) return; setOpen(false); setDone(null); setError(null); };

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-foreground/60 bg-surface px-4 py-3 sm:flex-row sm:items-center">
      <div className="flex-1 text-sm">
        <div className="font-medium">Uncommitted changes on <span className="font-mono">{view.branch}</span></div>
        <div className="text-[13px] text-secondary">{onProtected ? "Protected branch: changes go to a new branch and a pull request." : "Configuration edits live in the workspace until you commit them."}</div>
      </div>
      <Button onClick={() => setOpen(true)}><GitCommitHorizontal className="size-4" strokeWidth={1.75} /> Commit changes</Button>
      <Dialog
        open={open}
        onClose={close}
        title={done ? "Changes committed" : "Commit changes"}
        description={done ? undefined : <>Conventional Commits. {onProtected && <>Direct commits on <span className="font-mono">{view.branch}</span> are not allowed.</>}</>}
        footer={done ? <Button onClick={close}>Done</Button> : <><Button variant="ghost" onClick={close} disabled={pending}>Cancel</Button><Button disabled={pending || !canSubmit} onClick={submit}>{pending ? "Working…" : pullRequest ? "Commit and open PR" : "Commit"}</Button></>}
      >
        {done ? (
          <div className="space-y-2 text-sm">
            <div>Committed on <span className="font-mono">{done.branch}</span>{push || pullRequest ? " and pushed." : "."}</div>
            {done.url && <a href={done.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 underline underline-offset-4">Open pull request <ExternalLink className="size-3.5" strokeWidth={1.75} /></a>}
          </div>
        ) : (
          <div className="space-y-3">
            <Field label="Message"><Input value={message} onChange={(e) => setMessage(e.target.value)} className="font-mono" autoFocus /></Field>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={newBranch} onChange={(e) => { setNewBranch(e.target.checked); if (!e.target.checked) setPullRequest(false); }} disabled={onProtected} /> Commit on a new branch{onProtected && <span className="text-xs text-secondary">required here</span>}</label>
            {newBranch && (
              <div className="space-y-2 rounded-md border border-border p-3">
                <div className="flex flex-wrap gap-1">
                  {KINDS.map((k) => <button key={k} type="button" onClick={() => setKind(k)} aria-pressed={kind === k} className={cn("h-8 rounded-md border px-2.5 font-mono text-xs", kind === k ? "border-foreground" : "border-border text-secondary hover:border-border-hover")}>{k}</button>)}
                </div>
                <div className="grid gap-2 sm:grid-cols-2">
                  <Field label="Code"><Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="42" className="font-mono" /></Field>
                  <Field label="Slug"><Input value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="optional" className="font-mono" /></Field>
                </div>
                <div className="text-xs text-secondary">Branch <span className="font-mono text-foreground">{branchName}</span></div>
              </div>
            )}
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={push || pullRequest} onChange={(e) => setPush(e.target.checked)} disabled={!hasRemote || pullRequest} /> Push after committing</label>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={pullRequest} onChange={(e) => setPullRequest(e.target.checked)} disabled={!hasRemote || (!newBranch && onProtected)} /> Open a pull request</label>
            {!hasRemote && <p className="text-xs text-muted-foreground">No remote: push and pull request need a repository on a code host.</p>}
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
  const [picked, setPicked] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  return (
    <Panel>
      <PanelHeader title="Deploy target" aside={current ? <Badge className="font-mono">{current}</Badge> : <Badge>Not configured</Badge>} />
      <PanelBody className="space-y-3">
        <p className="text-sm text-secondary">Applies the cloud overlay's files to the workspace and records <span className="font-mono">[deploy] target</span> in <span className="font-mono">platform.toml</span>. Replaces the previous target.</p>
        {clouds.length === 0 ? (
          <p className="text-sm text-muted-foreground">No overlay supports {view.type ?? "this type"} / {view.language ?? "this language"}.</p>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2">
            {clouds.map((c) => {
              const active = c.name === current;
              return (
                <button key={c.name} type="button" disabled={pending || active || !view.can["app.configure"]} onClick={() => setPicked(c.name)} className={cn("flex items-start gap-3 rounded-md border p-3 text-left transition-colors", active ? "border-foreground" : "border-border hover:border-border-hover")}>
                  <Cloud className="mt-0.5 size-4 shrink-0 text-secondary" strokeWidth={1.75} />
                  <span className="min-w-0 flex-1"><span className="block font-mono text-sm">{c.name}</span><span className="block text-xs text-muted-foreground">{c.description}</span></span>
                  <CheckIndicator selected={active} />
                </button>
              );
            })}
          </div>
        )}
        {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
      </PanelBody>
      <ConfirmDialog
        open={picked !== null}
        onClose={() => setPicked(null)}
        title={`Set deploy target to ${picked}?`}
        description={current ? `Replaces ${current}. Overlay files are written into the workspace; commit them afterwards.` : "Overlay files are written into the workspace; commit them afterwards."}
        confirmLabel="Apply overlay"
        pending={pending}
        onConfirm={() => { const t = picked; if (t) start(async () => { setError(null); const r = await setCloudTarget(view.projectId, view.registryId, t); setPicked(null); if (r.ok) router.refresh(); else setError(r.error); }); }}
      />
    </Panel>
  );
}

function ServicesPanel({ view, services }: { view: AppView; services: ServiceOption[] }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(services[0]?.name ?? "");
  const [provider, setProvider] = useState<string>(services[0]?.providers[0] ?? "");
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const chosen = services.find((s) => s.name === name);

  return (
    <Panel>
      <PanelHeader title="Services" aside={<Button size="sm" variant="outline" disabled={services.length === 0 || !view.can["app.configure"]} onClick={() => setOpen(true)}>Add service</Button>} />
      <PanelBody className="space-y-2 text-sm">
        {view.services.length === 0 ? <p className="text-secondary">No services. Databases, caches and storage come as <span className="font-mono">services/&lt;name&gt;/</span> with up and link scripts.</p> : (
          <ul className="space-y-1.5">
            {view.services.map((s) => <li key={s} className="flex items-center gap-2"><Check className="size-3.5" strokeWidth={2.5} /><span className="font-mono text-[13px]">{s}</span></li>)}
          </ul>
        )}
        {error && <div className="rounded-md border border-foreground px-3 py-2">{error}</div>}
      </PanelBody>
      <Dialog
        open={open}
        onClose={() => !pending && setOpen(false)}
        title="Add service"
        description="Writes services/<name>/ into the workspace and records it under [services]."
        footer={<><Button variant="ghost" onClick={() => setOpen(false)} disabled={pending}>Cancel</Button><Button disabled={pending || !name} onClick={() => start(async () => { setError(null); const r = await addService(view.projectId, view.registryId, name, provider || null); if (r.ok) { setOpen(false); router.refresh(); } else setError(r.error); })}>{pending ? "Adding…" : "Add service"}</Button></>}
      >
        <div className="space-y-3">
          <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">Service</span>
            <Select mono value={name} onChange={(v) => { setName(v); setProvider(services.find((s) => s.name === v)?.providers[0] ?? ""); }} options={services.map((s) => ({ value: s.name, label: s.name }))} />
          </label>
          {chosen && chosen.providers.length > 0 && (
            <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">Provider</span>
              <Select mono value={provider} onChange={setProvider} options={chosen.providers.map((p) => ({ value: p, label: p }))} />
            </label>
          )}
          {chosen && <p className="text-xs text-muted-foreground">{chosen.description}</p>}
        </div>
      </Dialog>
    </Panel>
  );
}

function ManifestPanel({ view }: { view: AppView }) {
  const router = useRouter();
  const [content, setContent] = useState(view.manifest);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [pending, start] = useTransition();
  const dirty = content !== view.manifest;

  return (
    <Panel>
      <PanelHeader title="platform.toml" aside={<Button size="sm" disabled={pending || !dirty || !view.can["app.configure"]} onClick={() => start(async () => { setError(null); const r = await saveManifest(view.projectId, view.registryId, content); if (r.ok) { setSaved(true); setTimeout(() => setSaved(false), 1500); router.refresh(); } else setError(r.error); })}>{saved ? <Check className="size-4" strokeWidth={2.5} /> : <Save className="size-4" strokeWidth={1.75} />} {pending ? "Saving…" : saved ? "Saved" : "Save"}</Button>} />
      <PanelBody className="space-y-2">
        <textarea value={content} onChange={(e) => setContent(e.target.value)} readOnly={!view.can["app.configure"]} spellCheck={false} rows={Math.max(12, content.split("\n").length + 1)} className="w-full rounded-md px-3 py-2 font-mono text-xs leading-5" />
        {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
        <p className="text-xs text-muted-foreground">Validated as TOML on save. The name, type, language, CI, source host, release strategy and deploy target all live here.</p>
      </PanelBody>
    </Panel>
  );
}
