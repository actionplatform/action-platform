"use client";

import { BookMarked, ChevronDown, ExternalLink, Plus, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { addSource, removeSource } from "./actions";

export type SourceRow = { id: string | null; name: string; url: string; ref: string; ok: boolean; error: string | null; projects: number; clouds: number; services: number; official: boolean };

function webUrl(url: string): string | null {
  const m = url.match(/^(?:https?:\/\/|git@)([^/:]+)[/:](.+?)(?:\.git)?$/);
  return m ? `https://${m[1]}/${m[2]}` : null;
}

export function TemplateSources({ sources, canManage }: { sources: SourceRow[]; canManage: boolean }) {
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<SourceRow | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const [expanded, setExpanded] = useState(false);
  const official = sources.find((s) => s.official) ?? sources[0];
  const summary = sources.length === 1 && official ? `${official.projects} projects` : `${sources.length} repositories`;

  return (
    <section className="mb-4 overflow-hidden rounded-[9px] border border-border bg-surface md:mb-6">
      <header className="hidden min-h-12 flex-wrap items-center justify-between gap-x-3 gap-y-2 border-b border-border px-4 py-2 md:flex">
        <h2 className="flex items-center gap-2 text-sm font-semibold"><BookMarked className="size-4 text-secondary" strokeWidth={1.75} /> Template repositories</h2>
        {canManage && <Button size="sm" variant="outline" onClick={() => setAdding(true)}><Plus className="size-3.5" strokeWidth={2} /> Add repository</Button>}
      </header>
      <div className="flex items-center gap-1 pl-4 pr-1 md:hidden">
        <button type="button" aria-expanded={expanded} onClick={() => setExpanded((v) => !v)} className="flex min-h-12 min-w-0 flex-1 items-center gap-3 py-2 text-left focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground rounded-sm">
          <BookMarked className="size-4 shrink-0 text-secondary" strokeWidth={1.75} />
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-semibold">{sources.length === 1 && official?.official ? "Official repository" : "Template repositories"}</span>
            <span className="block text-xs text-secondary">{summary}</span>
          </span>
          <ChevronDown className={cn("size-4 shrink-0 text-secondary transition-transform", expanded && "rotate-180")} strokeWidth={1.75} aria-hidden="true" />
        </button>
        {canManage && <button type="button" aria-label="Add repository" onClick={() => setAdding(true)} className="flex size-11 shrink-0 items-center justify-center rounded-md text-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground"><Plus className="size-4" strokeWidth={2} /></button>}
      </div>
      <ul className={cn("divide-y divide-border-subtle border-t border-border-subtle md:block md:border-t-0", expanded ? "block" : "hidden")}>
        {sources.map((s) => {
          const link = webUrl(s.url);
          return (
            <li key={s.name} className="flex flex-col gap-1.5 px-4 py-3 text-sm sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-4 sm:gap-y-1">
              <div className="flex min-w-0 items-center gap-2 sm:flex-1">
                <span className="truncate font-mono">{s.name}</span>
                {s.official ? <Badge tone="inverse" className="shrink-0">Official</Badge> : <Badge className="shrink-0">{s.projects === 1 && s.clouds === 0 && s.services === 0 ? "Repository" : "Catalog"}</Badge>}
                {!s.ok && <Badge tone="bad" className="shrink-0">Unavailable</Badge>}
                {canManage && !s.official && <button type="button" title="Remove repository" aria-label={`Remove ${s.name}`} disabled={pending} onClick={() => setRemoving(s)} className="ml-auto flex size-11 shrink-0 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground sm:hidden"><Trash2 className="size-4" strokeWidth={1.75} /></button>}
              </div>
              <div className="flex min-w-0 items-center gap-2 font-mono text-xs text-secondary">
                {link ? <a href={link} target="_blank" rel="noopener noreferrer" className="inline-flex min-w-0 items-center gap-1 hover:text-foreground"><span className="truncate">{s.url.replace(/^https?:\/\//, "").replace(/\.git$/, "")}</span> <ExternalLink className="size-3 shrink-0" strokeWidth={1.75} /></a> : <span className="truncate">{s.url}</span>}
                <span aria-hidden className="shrink-0">@</span><span className="shrink-0">{s.ref}</span>
              </div>
              <div className="text-xs text-secondary">{s.ok ? `${s.projects} projects · ${s.clouds} clouds · ${s.services} services` : s.error}</div>
              {canManage && !s.official && <button type="button" title="Remove repository" aria-label={`Remove ${s.name}`} disabled={pending} onClick={() => setRemoving(s)} className="hidden size-8 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground sm:flex"><Trash2 className="size-4" strokeWidth={1.75} /></button>}
            </li>
          );
        })}
      </ul>
      {error && <div className="border-t border-border px-4 py-2 text-sm">{error}</div>}
      <AddSourceDialog open={adding} onClose={() => setAdding(false)} />
      <ConfirmDialog
        open={removing !== null}
        onClose={() => setRemoving(null)}
        title={`Remove ${removing?.name}?`}
        description="Its templates disappear from the catalog. Apps already created from them are untouched."
        confirmLabel="Remove"
        danger
        pending={pending}
        onConfirm={() => { const s = removing; if (s?.id) start(async () => { setError(null); const r = await removeSource(s.id!); setRemoving(null); if (!r.ok) setError(r.error); }); }}
      />
    </section>
  );
}

function AddSourceDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [ref, setRef] = useState("main");
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const close = () => { if (pending) return; onClose(); setName(""); setUrl(""); setRef("main"); setError(null); };

  return (
    <Dialog
      open={open}
      onClose={close}
      title="Add a template repository"
      description="Any git repository. It becomes a template: new apps start as a copy of it, and the platform adds platform.toml, hooks and CI when they are missing. A repository with an index.json is read as a full catalog instead. Private repositories use the connected code host."
      footer={<><Button variant="ghost" onClick={close} disabled={pending}>Cancel</Button><Button disabled={pending || !name.trim() || !url.trim()} onClick={() => start(async () => { setError(null); const r = await addSource({ name, url, ref }); if (r.ok) close(); else setError(r.error); })}>{pending ? "Adding…" : "Add repository"}</Button></>}
    >
      <div className="space-y-3">
        <Field label="Name" hint="Shown on the template card"><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="starter-api" className="font-mono" autoFocus /></Field>
        <Field label="Git URL"><Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://github.com/acme/starter-api.git" className="font-mono" /></Field>
        <Field label="Branch or tag"><Input value={ref} onChange={(e) => setRef(e.target.value)} className="font-mono" /></Field>
        {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
      </div>
    </Dialog>
  );
}
