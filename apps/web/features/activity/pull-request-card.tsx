"use client";

import { ArrowUpRight, GitBranch, GitPullRequest } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ActionField, ActionFields, ActionForm, ActionSummary } from "@/components/ui/action-form";
import { Badge } from "@/components/ui/badge";
import { ConfirmDialog } from "@/components/ui/dialog";
import { Hint } from "@/components/ui/hint";
import { Input, Textarea } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useAction } from "@/lib/use-action";
import { checkoutBranch, openPullRequest, proposePullRequest } from "@/features/activity/actions";
import { RunAlert, summarize } from "@/features/deployments";
import type { AppView } from "@/features/projects";
import { NewBranchDialog } from "./flow-panel";

type Proposal = { head: string; base: string; title: string; body: string; commits: string[] };
type Opened = { number: number; url: string };

export function PullRequestCard({ view }: { view: AppView }) {
  const router = useRouter();
  const [branchOpen, setBranchOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [draft, setDraft] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [switchError, setSwitchError] = useState<string | null>(null);
  const [base, setBase] = useState("");

  const action = useAction<Proposal, Opened>({
    preview: () => proposePullRequest(view.projectId, view.registryId),
    run: () => openPullRequest(view.projectId, view.appId, view.registryId, { base, title: title.trim(), body, draft }),
    onDone: (r) => router.push(`/projects/${view.projectId}/apps/${view.appId}/activity?opened=${r.number}`),
  });

  useEffect(() => {
    if (action.previewed) { setTitle(action.previewed.title); setBody(action.previewed.body); setBase(action.previewed.base); }
  }, [action.previewed]);

  const canFlow = view.can["app.flow"] && !!view.repositoryUrl;
  const blocker = !view.can["app.flow"] ? "Your role cannot open pull requests." : !view.repositoryUrl ? "Push the repository first." : view.onProtectedBranch ? `Pull requests start from a <kind>/<code> branch; ${view.branch} is protected. Create or check out one.` : view.workingTree !== "clean" ? "Commit or discard the pending changes first." : null;
  const ready = canFlow && !blocker && !!action.previewed && !!title.trim();

  const checkout = (branch: string) => {
    setSwitching(true);
    setSwitchError(null);
    action.reset();
    checkoutBranch(view.projectId, view.registryId, branch).then((r) => { setSwitching(false); if (r.ok) router.refresh(); else setSwitchError(r.error); });
  };

  const branches = [...(!view.branches.some((b) => b.name === view.branch) && view.branch ? [{ value: view.branch, label: view.branch }] : []), ...view.branches.map((b) => ({ value: b.name, label: b.name, hint: b.protected ? "protected" : b.kind ?? undefined }))];
  const proposal = action.previewed;

  return (
    <ActionForm
      title="Open pull request"
      aside={<Badge className="font-mono">{view.branch || "—"}</Badge>}
      primary={{ label: "Open pull request", icon: GitPullRequest, onClick: action.confirm, disabled: !ready, busy: action.step === "running", busyLabel: "Opening…" }}
      secondary={proposal ? { label: "Prepare again", icon: GitBranch, onClick: action.preview, disabled: !canFlow || !!blocker, busy: action.step === "previewing", busyLabel: "Preparing…" } : { label: "Prepare", icon: GitBranch, onClick: action.preview, disabled: !canFlow || !!blocker, busy: action.step === "previewing", busyLabel: "Preparing…" }}
      blocker={action.error || switchError ? null : blocker ?? (!proposal ? "Prepare reads the commits on the branch and drafts the title and body." : null)}
      summary={[{ label: "Head", value: proposal?.head ?? view.branch }, { label: "Base", value: proposal?.base ?? "—" }, { label: "Commits", value: proposal ? String(proposal.commits.length) : "—" }, { label: "Kind", value: draft ? "draft" : "ready for review" }]}
      alerts={
        <>
          {switchError && <RunAlert tone="danger" title="Could not check out" summary={summarize(switchError)} log={switchError} />}
          {action.error && <RunAlert tone="danger" title="Pull request failed" summary={summarize(action.error)} log={action.error} />}
          {action.result && <RunAlert tone="success" title={`Opened #${action.result.number}`} summary={action.result.url} />}
        </>
      }
      dialogs={
        <>
          <NewBranchDialog view={view} open={branchOpen} onClose={() => setBranchOpen(false)} />
          <ConfirmDialog open={action.step === "confirming"} onClose={action.cancel} title={`Open pull request from ${proposal?.head ?? view.branch}?`} confirmLabel="Open pull request" pending={action.busy} onConfirm={action.execute}>
            <ActionSummary items={[{ label: "Head", value: proposal?.head ?? view.branch }, { label: "Base", value: proposal?.base ?? "—" }, { label: "Title", value: title.trim() || "—" }, { label: "Kind", value: draft ? "draft" : "ready for review" }]} />
            <p className="mt-4 text-sm text-secondary">Audits git-flow on the branch, then opens the pull request on the code host. Review and merge it there; the next sync picks it up.</p>
          </ConfirmDialog>
        </>
      }
    >
      <ActionFields>
        <ActionField label="Branch" hint={<Hint text="The head of the pull request — the branch the app is checked out on. Pick another to switch, or create one." />}>
          <div className="flex items-center gap-2">
            <Select size="lg" mono className="min-w-0 flex-1" icon={<GitBranch className="size-4" strokeWidth={1.75} />} value={view.branch} onChange={checkout} disabled={switching || view.workingTree !== "clean" || !view.can["app.flow"]} options={branches} />
            <button type="button" onClick={() => setBranchOpen(true)} disabled={switching || view.workingTree !== "clean" || !view.can["app.flow"]} className="inline-flex h-[42px] shrink-0 items-center gap-1.5 rounded-[7px] border border-border px-3 text-sm hover:border-border-hover hover:bg-surface-hover disabled:opacity-40">New branch</button>
          </div>
        </ActionField>
        <ActionField label="Base" hint={<Hint text="Where the branch merges, from the git-flow rules: develop or main." />}>
          <div className="flex h-[42px] items-center rounded-[7px] border border-dashed border-border px-3 font-mono text-sm text-muted-foreground">{proposal?.base ?? "Prepare to see"}</div>
        </ActionField>
        <ActionField label="Title">
          <Input className="h-[42px] rounded-[7px]" value={title} onChange={(e) => setTitle(e.target.value)} placeholder={proposal ? "" : "Prepare fills it from the commits"} disabled={!proposal} />
        </ActionField>
        <ActionField label="Body" hint={<label className="ml-auto flex items-center gap-1.5 text-xs text-secondary"><input type="checkbox" checked={draft} onChange={(e) => setDraft(e.target.checked)} /> Draft</label>}>
          <Textarea value={body} onChange={(e) => setBody(e.target.value)} rows={4} className="min-h-[42px] rounded-[7px] font-mono text-[13px]" disabled={!proposal} />
        </ActionField>
      </ActionFields>
      {action.result && <a href={action.result.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-[13px] text-secondary hover:text-foreground">{action.result.url} <ArrowUpRight className="size-3.5" strokeWidth={1.75} /></a>}
    </ActionForm>
  );
}
