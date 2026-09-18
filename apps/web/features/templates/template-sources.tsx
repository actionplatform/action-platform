"use client";

import { BookMarked, ExternalLink, Plus, Trash2 } from "lucide-react";
import { Cell, DataTable, Inline } from "@/components/ui/data-table";
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
  const remove = (s: SourceRow) => canManage && !s.official ? <button type="button" title="Remove repository" aria-label={`Remove ${s.name}`} disabled={pending} onClick={() => setRemoving(s)} className="inline-flex size-8 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground"><Trash2 className="size-4" strokeWidth={1.75} /></button> : null;
  const kind = (s: SourceRow) => (s.official ? <Badge tone="inverse">Official</Badge> : <Badge>{s.projects === 1 && s.clouds === 0 && s.services === 0 ? "Repository" : "Catalog"}</Badge>);
  const where = (s: SourceRow) => { const link = webUrl(s.url); const shown = s.url.replace(/^https?:\/\//, "").replace(/\.git$/, ""); return <Inline className="font-mono text-xs text-secondary">{link ? <a href={link} target="_blank" rel="noopener noreferrer" className="inline-flex min-w-0 items-center gap-1 hover:text-foreground"><span className="truncate">{shown}</span> <ExternalLink className="size-3 shrink-0" strokeWidth={1.75} /></a> : <span className="truncate">{s.url}</span>}<span aria-hidden>@</span><span className="shrink-0">{s.ref}</span></Inline>; };

  return (
    <div className="mb-4 space-y-3 md:mb-6">
      {error && <div className="rounded-md border border-border px-3 py-2 text-[13px] text-secondary">{error}</div>}
      <DataTable
        title="Template repositories"
        rows={sources}
        rowKey={(s) => s.name}
        noun={["repository", "repositories"]}
        minWidth={720}
        action={canManage ? <Button size="sm" variant="outline" onClick={() => setAdding(true)}><Plus className="size-3.5" strokeWidth={2} /> Add repository</Button> : undefined}
        empty={{ icon: BookMarked, title: "No template repository", text: "Add a git repository; new apps start as a copy of it." }}
        columns={[
          { key: "name", label: "Name", width: 28, render: (s) => <Inline><span className="truncate font-mono">{s.name}</span>{kind(s)}{!s.ok && <Badge tone="bad">Unavailable</Badge>}</Inline> },
          { key: "url", label: "Repository", width: 38, hide: "sm", render: where },
          { key: "contents", label: "Contents", width: 28, hide: "md", render: (s) => <Cell muted title={s.ok ? undefined : s.error ?? undefined}>{s.ok ? `${s.projects} projects · ${s.clouds} clouds · ${s.services} services` : s.error}</Cell> },
          { key: "actions", label: "", width: 6, align: "right", render: remove },
        ]}
      />
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
    </div>
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
