import { ExternalLink, GitBranch, GitPullRequest } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Panel, PanelHeader } from "@/components/ui/panel";
import type { CiState } from "@/lib/ci-kinds";
import type { StoredPullRequest } from "@/lib/pull-requests";
import { relativeTime } from "@/lib/time";
import { RunBadge, RunCiButton } from "@/features/ci";
import type { AppView } from "@/features/projects";
import { latestRunOn, openPullFrom, proposeBlocker } from "./current-branch";

type Props = { view: AppView; ci: CiState | null; pulls: StoredPullRequest[]; newHref: string; ciSettingsHref: string };

export function CurrentBranchCard({ view, ci, pulls, newHref, ciSettingsHref }: Props) {
  const openPull = openPullFrom(pulls, view.branch);
  const blocker = proposeBlocker(view, openPull);
  const connected = !!ci && ci.link.kind !== "none";
  const run = ci ? latestRunOn(ci.runs, view.branch) : null;

  return (
    <Panel>
      <PanelHeader
        title={<><GitBranch className="size-4 text-secondary" strokeWidth={1.75} /> Current branch</>}
        aside={<Badge className="font-mono">{view.branch || "—"}</Badge>}
      />
      <div className="divide-y divide-border-subtle">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3 text-sm">
          <span className="text-xs text-muted-foreground">CI</span>
          {!ci ? (
            <span className="text-secondary">CI status unavailable.</span>
          ) : !connected ? (
            <span className="text-secondary">No CI connected.{view.can["app.configure"] && <> <Link href={ciSettingsHref} className="text-foreground underline-offset-4 hover:underline">Connect CI</Link></>}</span>
          ) : run ? (
            <>
              <RunBadge status={run.status} />
              {run.url ? (
                <a href={run.url} target="_blank" rel="noopener noreferrer" className="inline-flex min-w-0 items-center gap-1 truncate hover:underline underline-offset-4">{run.name ?? `#${run.number}`} <ExternalLink className="size-3 shrink-0" strokeWidth={1.75} /></a>
              ) : (
                <span className="min-w-0 truncate">{run.name ?? `#${run.number}`}</span>
              )}
              {run.startedAt && <span className="text-xs text-secondary" suppressHydrationWarning>{relativeTime(run.startedAt)}</span>}
            </>
          ) : (
            <span className="text-secondary">No run on <span className="font-mono">{view.branch}</span> imported yet.</span>
          )}
          {connected && view.can["app.flow"] && <span className="ml-auto flex flex-wrap items-center gap-2"><RunCiButton projectId={view.projectId} appId={view.appId} link={ci.link} defaultRef={view.branch} /></span>}
        </div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3 text-sm">
          <span className="text-xs text-muted-foreground">Pull request</span>
          {openPull ? (
            <a href={openPull.url} target="_blank" rel="noopener noreferrer" className="inline-flex min-w-0 items-center gap-1 truncate hover:underline underline-offset-4">#{openPull.number} open <ExternalLink className="size-3 shrink-0" strokeWidth={1.75} /></a>
          ) : (
            <span className="min-w-0 text-secondary">{blocker ?? `${view.health.checked_commits} ${view.health.checked_commits === 1 ? "commit" : "commits"} to propose.`}</span>
          )}
          <span className="ml-auto flex flex-wrap items-center gap-2">
            {view.can["app.flow"] && view.repositoryUrl && <Link href={newHref} className={buttonVariants({ size: "sm", variant: "ghost" })}><GitBranch className="size-3.5" strokeWidth={2} /> Change branch</Link>}
            {blocker ? (
              <Button size="sm" disabled><GitPullRequest className="size-3.5" strokeWidth={2} /> Open pull request</Button>
            ) : (
              <Link href={newHref} className={buttonVariants({ size: "sm" })}><GitPullRequest className="size-3.5" strokeWidth={2} /> Open pull request</Link>
            )}
          </span>
        </div>
      </div>
    </Panel>
  );
}
