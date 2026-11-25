"use client";

import { Play } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { CI_LABELS, type CiLink } from "@/lib/ci-kinds";
import { call } from "@/lib/call";
import { startCi } from "./actions";

type Props = { projectId: string; appId: string; link: CiLink; defaultRef: string };

export function RunCiButton({ projectId, appId, link, defaultRef }: Props) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [ref, setRef] = useState(defaultRef);
  const [error, setError] = useState<string | null>(null);
  const [started, setStarted] = useState<{ id: string; url: string | null } | null>(null);
  const [pending, start] = useTransition();

  const run = () =>
    start(async () => {
      setError(null);
      const r = await call(() => startCi(projectId, appId, ref.trim()), (e) => ({ ok: false as const, error: e }), "Check the CI for the run.");
      if (!r.ok) { setError(r.error); return; }
      setStarted(r.data);
      setOpen(false);
      router.refresh();
    });

  return (
    <>
      <Button size="sm" variant="outline" onClick={() => { setStarted(null); setError(null); setOpen(true); }} disabled={pending}><Play className="size-3.5" strokeWidth={2} /> Run CI</Button>
      {started && <p role="status" className="basis-full text-[13px] text-secondary">Run started{started.url ? <> — <a href={started.url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-4 hover:text-foreground">open on the CI</a></> : "."} Its result shows here after the next sync.</p>}
      <Dialog open={open} onClose={() => !pending && setOpen(false)} title="Run the job" description={`${CI_LABELS[link.kind] ?? link.kind}${link.job ? ` · ${link.job}` : ""}`} footer={<><Button variant="ghost" onClick={() => setOpen(false)} disabled={pending}>Cancel</Button><Button onClick={run} disabled={pending || !ref.trim()}><Play className="size-3.5" strokeWidth={2} /> {pending ? "Starting…" : "Run"}</Button></>}>
        <Field label="Branch or tag" hint="The ref the run checks out."><Input value={ref} onChange={(e) => setRef(e.target.value)} className="font-mono" autoFocus /></Field>
        {error && <div role="alert" className="mt-3 rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
      </Dialog>
    </>
  );
}
