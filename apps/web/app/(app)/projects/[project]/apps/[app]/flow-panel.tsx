"use client";

import { ArrowUpRight, GitBranch, GitPullRequest } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { cn } from "@/lib/utils";
import { checkoutBranch, openPullRequest, planBranch, proposePullRequest, startBranch } from "../actions";
import type { AppView } from "./model";


export function FlowPanel({ view }: { view: AppView }) {
  const router = useRouter();
  const [branchOpen, setBranchOpen] = useState(false);
  const [prOpen, setPrOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const onProtected = view.onProtectedBranch;

  const checkout = (branch: string) =>
    start(async () => {
      setError(null);
      const r = await checkoutBranch(view.projectId, view.registryId, branch);
      if (r.ok) router.refresh(); else setError(r.error);
    });

  return (
    <Panel>
      <PanelHeader title="Git-flow" aside={<Badge className="font-mono">{view.branch || "—"}</Badge>} />
      <PanelBody className="space-y-4">
        {!view.can["app.flow"] && <p className="text-[13px] text-muted-foreground">Your role can view branches but not change them.</p>}
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button variant="outline" disabled={pending || view.workingTree !== "clean" || !view.can["app.flow"]} onClick={() => setBranchOpen(true)}><GitBranch className="size-4" strokeWidth={1.75} /> New branch</Button>
          <Button disabled={pending || onProtected || !view.repositoryUrl || !view.can["app.flow"]} onClick={() => setPrOpen(true)}><GitPullRequest className="size-4" strokeWidth={1.75} /> Open pull request</Button>
        </div>
        {onProtected && <p className="text-[13px] text-muted-foreground">Pull requests start from a <span className="font-mono">&lt;kind&gt;/&lt;code&gt;</span> branch. Create one, or check out an existing branch below.</p>}
        {view.workingTree !== "clean" && <p className="text-[13px] text-muted-foreground">The working tree has local changes; branching is disabled until it is clean.</p>}
        {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}

        <label className="block text-sm">
          <span className="mb-1 block text-xs text-secondary">Check out a branch</span>
          <Select mono value={view.branch} onChange={checkout} disabled={pending || view.workingTree !== "clean" || !view.can["app.flow"]} options={[...(!view.branches.some((b) => b.name === view.branch) && view.branch ? [{ value: view.branch, label: view.branch }] : []), ...view.branches.map((b) => ({ value: b.name, label: b.name, hint: b.protected ? "protected" : b.kind ?? undefined }))]} />
        </label>
      </PanelBody>

      <NewBranchDialog view={view} open={branchOpen} onClose={() => setBranchOpen(false)} />
      <PullRequestDialog view={view} open={prOpen} onClose={() => setPrOpen(false)} />
    </Panel>
  );
}

export function OpenPullRequestButton({ view }: { view: AppView }) {
  const [open, setOpen] = useState(false);
  const onProtected = view.onProtectedBranch;
  const reason = !view.can["app.flow"] ? "Your role cannot open pull requests." : !view.repositoryUrl ? "Push the repository first." : onProtected ? `Check out a <kind>/<code> branch first; ${view.branch} is protected.` : null;
  return (
    <>
      <Button size="sm" disabled={!!reason} title={reason ?? undefined} onClick={() => setOpen(true)}><GitPullRequest className="size-4" strokeWidth={1.75} /> Open pull request</Button>
      <PullRequestDialog view={view} open={open} onClose={() => setOpen(false)} />
    </>
  );
}

function NewBranchDialog({ view, open, onClose }: { view: AppView; open: boolean; onClose: () => void }) {
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

function PullRequestDialog({ view, open, onClose }: { view: AppView; open: boolean; onClose: () => void }) {
  const router = useRouter();
  const [proposal, setProposal] = useState<{ head: string; base: string; title: string; body: string; commits: string[] } | null>(null);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [draft, setDraft] = useState(false);
  const [result, setResult] = useState<{ number: number; url: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  useEffect(() => {
    if (!open) return;
    start(async () => {
      setError(null);
      const r = await proposePullRequest(view.projectId, view.registryId);
      if (r.ok) { setProposal(r.data); setTitle(r.data.title); setBody(r.data.body); } else setError(r.error);
    });
  }, [open, view.projectId, view.registryId]);

  const close = () => { if (pending) return; onClose(); setProposal(null); setResult(null); setError(null); };

  const submit = () =>
    start(async () => {
      if (!proposal) return;
      setError(null);
      const r = await openPullRequest(view.projectId, view.appId, view.registryId, { base: proposal.base, title, body, draft });
      if (r.ok) { setResult(r.data); router.refresh(); } else setError(r.error);
    });

  return (
    <Dialog
      open={open}
      onClose={close}
      title="Open pull request"
      description={proposal ? <><span className="font-mono">{proposal.head}</span> → <span className="font-mono">{proposal.base}</span> · {proposal.commits.length} {proposal.commits.length === 1 ? "commit" : "commits"}</> : "Audits git-flow, then opens it on the code host."}
      className="max-w-2xl"
      footer={
        result ? (
          <Button onClick={close}>Done</Button>
        ) : (
          <><Button variant="ghost" onClick={close} disabled={pending}>Cancel</Button><Button disabled={pending || !proposal || !title.trim()} onClick={submit}>{pending && proposal ? "Opening…" : "Open pull request"}</Button></>
        )
      }
    >
      {result ? (
        <div className="text-sm">Opened <a href={result.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-mono underline underline-offset-4">#{result.number} <ArrowUpRight className="size-3.5" /></a></div>
      ) : (
        <div className="space-y-3">
          {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
          {!proposal && !error && <div className="text-sm text-secondary">Preparing…</div>}
          {proposal && (
            <>
              <Field label="Title"><Input value={title} onChange={(e) => setTitle(e.target.value)} /></Field>
              <label className="block text-sm">
                <span className="mb-1 block text-xs text-secondary">Body</span>
                <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={8} className="w-full rounded-md px-3 py-2 font-mono text-xs" />
              </label>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={draft} onChange={(e) => setDraft(e.target.checked)} /> Open as draft</label>
            </>
          )}
        </div>
      )}
    </Dialog>
  );
}
