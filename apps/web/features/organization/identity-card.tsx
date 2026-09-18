"use client";

import { Check, GitCommitHorizontal } from "lucide-react";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { Field, Input } from "@/components/ui/input";
import { saveGitAuthor } from "./actions";

export function IdentityCard({ author, canManage }: { author: { name: string; email: string }; canManage: boolean }) {
  const [name, setName] = useState(author.name);
  const [email, setEmail] = useState(author.email);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const dirty = name !== author.name || email !== author.email;

  return (
    <Panel>
      <PanelHeader title={<><GitCommitHorizontal className="size-4 text-secondary" strokeWidth={1.75} /> Commit identity</>} description="Releases and configuration commits the platform makes for this workspace are signed with this name and email." />
      <div className="p-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Name"><Input value={name} onChange={(e) => setName(e.target.value)} disabled={!canManage} /></Field>
          <Field label="Email"><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="font-mono" disabled={!canManage} /></Field>
        </div>
        <div className="mt-3 flex items-center gap-3">
          {canManage && <Button size="sm" disabled={pending || !dirty} onClick={() => start(async () => { setError(null); const r = await saveGitAuthor({ name, email }); if (r.ok) { setSaved(true); setTimeout(() => setSaved(false), 1500); } else setError(r.error); })}>{saved ? <Check className="size-3.5" strokeWidth={2.5} /> : null} {pending ? "Saving…" : saved ? "Saved" : "Save"}</Button>}
          <span className="text-[13px] text-secondary">Commits appear on the code host as <span className="font-mono text-foreground">{name || "…"} &lt;{email || "…"}&gt;</span>.</span>
        </div>
        {error && <div className="mt-3 rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
      </div>
    </Panel>
  );
}
