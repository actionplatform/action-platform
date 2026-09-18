"use client";

import { GitMerge, GitPullRequest, GitPullRequestArrow, GitPullRequestClosed } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { DataList } from "@/components/ui/data-list";
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

function StateBadge({ r }: { r: StoredPullRequest }) {
  return <Badge tone={r.state === "merged" ? "inverse" : r.state === "open" ? "ok" : "neutral"}>{r.state === "merged" ? "Merged" : r.state === "open" ? (r.draft ? "Draft" : "Open") : "Closed"}</Badge>;
}

const when = (r: StoredPullRequest) => (r.state === "merged" && r.mergedAt ? `merged ${relativeTime(r.mergedAt)}` : r.state === "closed" ? `closed ${relativeTime(r.updatedAt)}` : `opened ${relativeTime(r.createdAt)}`);

export function PullRequestsTable({ rows, currentBranch, repositoryUrl, newHref, hasHost }: { rows: StoredPullRequest[]; currentBranch: string; repositoryUrl: string | null; newHref: string | null; hasHost: boolean }) {
  const source = rows[0]?.source ?? null;
  const open = rows.filter((r) => r.state === "open").length;
  return (
    <DataList
      title="Pull requests"
      rows={rows}
      rowKey={(r) => String(r.number)}
      noun={["pull request", "pull requests"]}
      meta={rows.length > 0 ? <>{open} open{source && <> · {SOURCE[source] ?? source}</>}</> : undefined}
      newHref={newHref}
      newLabel="New pull request"
      empty={{ icon: GitPullRequest, title: "No pull requests yet", text: hasHost ? "Open the first one with New pull request. Sync imports existing ones from the code host." : "Connect a code host and push the repository to track pull requests." }}
      columns={[
        { key: "state", label: "State", render: (r) => <span className="flex items-center gap-2"><StateIcon state={r.state} draft={r.draft} /><StateBadge r={r} /></span> },
        { key: "title", label: "Title", className: "max-w-0 w-full", render: (r) => <span className="flex items-center gap-2 truncate"><a href={r.url} target="_blank" rel="noopener noreferrer" className="truncate font-medium hover:underline underline-offset-4">{r.title}</a><span className="font-mono text-xs text-muted-foreground">#{r.number}</span>{r.head === currentBranch && <Badge tone="ok">Current branch</Badge>}</span> },
        { key: "branches", label: "Branches", render: (r) => <span className="font-mono text-xs text-secondary">{r.head} <span aria-hidden>→</span> {r.base}</span> },
        { key: "author", label: "Author", render: (r) => <span className="text-secondary">{r.author ?? "—"}</span> },
        { key: "when", label: "When", render: (r) => <span className="whitespace-nowrap text-secondary">{when(r)}</span> },
      ]}
      card={(r) => (
        <>
          <div className="flex flex-wrap items-center gap-2"><StateIcon state={r.state} draft={r.draft} /><a href={r.url} target="_blank" rel="noopener noreferrer" className="truncate font-medium hover:underline underline-offset-4">{r.title}</a><span className="font-mono text-xs text-muted-foreground">#{r.number}</span><StateBadge r={r} /></div>
          <div className="mt-1 flex flex-wrap gap-x-2 text-xs text-secondary"><span className="font-mono">{r.head} → {r.base}</span>{r.author && <><span aria-hidden>·</span><span>{r.author}</span></>}<span aria-hidden>·</span><span>{when(r)}</span></div>
        </>
      )}
      action={repositoryUrl && rows.length > 0 ? <a href={`${repositoryUrl}/pulls`} target="_blank" rel="noopener noreferrer" className="hidden text-[13px] text-secondary hover:text-foreground sm:block">View all on {SOURCE[source ?? ""] ?? "the host"}</a> : undefined}
    />
  );
}
