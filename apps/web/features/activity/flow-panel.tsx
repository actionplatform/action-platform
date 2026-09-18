"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { planBranch, startBranch } from "@/features/activity/actions";
import type { AppView } from "@/features/projects";


export function NewBranchDialog({ view, open, onClose }: { view: AppView; open: boolean; onClose: () => void }) {
  const router = useRouter();
  const [kind, setKind] = useState("feature");
  const [code, setCode] = useState("");
  const [slug, setSlug] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const [plan, setPlan] = useState<{ branch: string; base: string } | null>(null);
  useEffect(() => {
    let live = true;
    const timer = setTimeout(() => { planBranch(view.registryId, kind, code, slug).then((r) => { if (live && r.ok) setPlan(r.data); }); }, 150);
    return () => { live = false; clearTimeout(timer); };
  }, [view.registryId, kind, code, slug]);
  const name = plan?.branch ?? `${kind}/…`;
  const base = plan?.base ?? "…";

  const submit = () =>
    start(async () => {
      setError(null);
      const r = await startBranch(view.projectId, view.appId, view.registryId, { kind, code: code.trim(), slug: slug.trim(), push: true });
      if (r.ok) { onClose(); router.refresh(); } else setError(r.error);
    });

  return (
    <Dialog
      open={open}
      onClose={() => !pending && onClose()}
      title="New branch"
      description={<>Creates <span className="font-mono">{name}</span> from <span className="font-mono">{base}</span> after pulling it.</>}
      footer={<><Button variant="ghost" onClick={onClose} disabled={pending}>Cancel</Button><Button disabled={pending || !code.trim()} onClick={submit}>{pending ? "Creating…" : "Create branch"}</Button></>}
    >
      <div className="space-y-3">
        <div>
          <div className="mb-1 text-xs text-secondary">Kind</div>
          <div className="flex flex-wrap gap-1.5">
            {view.branchKinds.map((k) => (
              <button key={k} type="button" onClick={() => setKind(k)} aria-pressed={kind === k} className={cn("h-8 rounded-md border px-2.5 font-mono text-xs transition-colors", kind === k ? "border-foreground bg-foreground text-primary-foreground" : "border-border text-secondary hover:border-border-hover hover:text-foreground")}>{k}</button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Code" hint="Issue or ticket: 42, PROJ-7"><Input value={code} onChange={(e) => setCode(e.target.value)} className="font-mono" placeholder="42" autoFocus /></Field>
          <Field label="Slug" hint="Optional words"><Input value={slug} onChange={(e) => setSlug(e.target.value)} className="font-mono" placeholder="login" /></Field>
        </div>
        <p className="text-xs text-muted-foreground">The branch is created from its git-flow base and pushed; the app is then checked out on it.</p>
        {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
      </div>
    </Dialog>
  );
}
