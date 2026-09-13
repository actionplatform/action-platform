"use client";

import { BookMarked, ExternalLink, Plus, Trash2 } from "lucide-react";
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

  return (
    <section className="mb-6 overflow-hidden rounded-[9px] border border-border bg-surface">
      <header className="flex h-12 items-center justify-between gap-3 border-b border-border px-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold"><BookMarked className="size-4 text-secondary" strokeWidth={1.75} /> Template repositories</h2>
        {canManage && <Button size="sm" variant="outline" onClick={() => setAdding(true)}><Plus className="size-3.5" strokeWidth={2} /> Add repository</Button>}
      </header>
      <ul className="divide-y divide-border-subtle">
        {sources.map((s) => {
          const link = webUrl(s.url);
          return (
            <li key={s.name} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-sm">
              <div className="flex min-w-0 flex-1 items-center gap-2">
                <span className="font-mono">{s.name}</span>
                {s.official ? <Badge tone="inverse">Official</Badge> : <Badge>{s.projects === 1 && s.clouds === 0 && s.services === 0 ? "Repository" : "Catalog"}</Badge>}
                {!s.ok && <Badge tone="bad">Unavailable</Badge>}
              </div>
              <div className="flex min-w-0 items-center gap-2 font-mono text-xs text-secondary">
                {link ? <a href={link} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 truncate hover:text-foreground">{s.url.replace(/^https?:\/\//, "").replace(/\.git$/, "")} <ExternalLink className="size-3" strokeWidth={1.75} /></a> : <span className="truncate">{s.url}</span>}
                <span aria-hidden>@</span><span>{s.ref}</span>
              </div>
              <div className="text-xs text-secondary">{s.ok ? `${s.projects} projects · ${s.clouds} clouds · ${s.services} services` : s.error}</div>
              {canManage && !s.official && <button type="button" title="Remove repository" aria-label={`Remove ${s.name}`} disabled={pending} onClick={() => setRemoving(s)} className="flex size-8 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground"><Trash2 className="size-4" strokeWidth={1.75} /></button>}
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
      description="Any git repository. It becomes a template: new apps start as a copy of it, and the platform adds platform.toml, hooks and CI when they are missing. A repository with an index.toml is read as a full catalog instead. Private repositories use the connected code host."
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
