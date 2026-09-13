import { GitPullRequest, GitPullRequestArrow, GitPullRequestClosed, GitMerge } from "lucide-react";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/panel";
import type { PullRequest, StoredPullRequest } from "@/lib/pull-requests";
import { relativeTime } from "@/lib/time";

const SOURCE: Record<string, string> = { github: "GitHub", gitlab: "GitLab", bitbucket: "Bitbucket" };

function StateIcon({ state, draft }: { state: PullRequest["state"]; draft: boolean }) {
  const cls = "size-4 shrink-0";
  if (state === "merged") return <GitMerge className={cls} strokeWidth={1.75} />;
  if (state === "closed") return <GitPullRequestClosed className={`${cls} text-muted-foreground`} strokeWidth={1.75} />;
  if (draft) return <GitPullRequestArrow className={`${cls} text-secondary`} strokeWidth={1.75} />;
  return <GitPullRequest className={cls} strokeWidth={1.75} />;
}

export function PullRequestsCard({ rows, hasHost, currentBranch, branches, repositoryUrl, action }: { rows: StoredPullRequest[]; hasHost: boolean; currentBranch: string; branches: string[]; repositoryUrl: string | null; action?: ReactNode }) {
  const existing = new Set(branches);
  const open = rows.filter((r) => r.state === "open").length;
  const source = rows[0]?.source ?? null;

  return (
    <Panel>
      <PanelHeader title="Pull requests" aside={<div className="flex items-center gap-3">{rows.length > 0 && source && <span className="hidden text-[13px] text-secondary sm:block">{open} open · {rows.length} total · {SOURCE[source] ?? source}</span>}{action}</div>} />
      {rows.length === 0 ? (
        <div className="flex flex-col items-center px-4 py-10 text-center">
          <GitPullRequest className="size-5 text-secondary" strokeWidth={1.5} />
          <div className="mt-3 text-sm font-medium">No pull requests yet</div>
          <div className="text-[13px] text-secondary">{hasHost ? "Start a branch above, commit, then open one from here. Sync imports existing ones from the code host." : "Connect a code host and push the repository to track pull requests."}</div>
        </div>
      ) : (
        <ul className="divide-y divide-border-subtle border-t border-border-subtle">
          {rows.map((r) => (
            <li key={r.number} className="flex items-start gap-3 px-4 py-3">
              <span className="mt-0.5"><StateIcon state={r.state} draft={r.draft} /></span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <a href={r.url} target="_blank" rel="noopener noreferrer" className="truncate text-sm font-medium hover:underline underline-offset-4">{r.title}</a>
                  <span className="font-mono text-xs text-muted-foreground">#{r.number}</span>
                  <Badge tone={r.state === "merged" ? "inverse" : r.state === "open" ? "ok" : "neutral"}>{r.state === "merged" ? "Merged" : r.state === "open" ? (r.draft ? "Draft" : "Open") : "Closed"}</Badge>
                  {r.head === currentBranch && <Badge tone="ok">Current branch</Badge>}
                </div>
                <div className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-secondary">
                  {existing.has(r.head) || r.state === "open" ? (
                    <><span className="font-mono">{r.head}</span><span aria-hidden>→</span><span className="font-mono">{r.base}</span></>
                  ) : (
                    <span>into <span className="font-mono">{r.base}</span></span>
                  )}
                  {r.author && <><span aria-hidden>·</span><span>{r.author}</span></>}
                  <span aria-hidden>·</span>
                  <span>{r.state === "merged" && r.mergedAt ? `merged ${relativeTime(r.mergedAt)}` : r.state === "closed" ? `closed ${relativeTime(r.updatedAt)}` : `opened ${relativeTime(r.createdAt)}`}</span>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
      {repositoryUrl && rows.length > 0 && (
        <div className="border-t border-border-subtle px-4 py-2 text-xs"><a href={`${repositoryUrl}/pulls`} target="_blank" rel="noopener noreferrer" className="text-secondary hover:text-foreground">View all on {SOURCE[source ?? ""] ?? "the host"}</a></div>
      )}
    </Panel>
  );
}
