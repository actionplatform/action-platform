"use client";

import { GitMerge, GitPullRequest, GitPullRequestArrow, GitPullRequestClosed } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Cell, DataTable, Inline } from "@/components/ui/data-table";
import type { PullRequest, StoredPullRequest } from "@/lib/pull-requests";
import type { Paged } from "@/lib/page";
import { relativeTime } from "@/lib/time";

const SOURCE: Record<string, string> = { github: "GitHub", gitlab: "GitLab", bitbucket: "Bitbucket" };

function StateIcon({ state, draft }: { state: PullRequest["state"]; draft: boolean }) {
  const cls = "size-4 shrink-0";
  if (state === "merged") return <GitMerge className={cls} strokeWidth={1.75} />;
  if (state === "closed") return <GitPullRequestClosed className={`${cls} text-muted-foreground`} strokeWidth={1.75} />;
  if (draft) return <GitPullRequestArrow className={`${cls} text-secondary`} strokeWidth={1.75} />;
  return <GitPullRequest className={cls} strokeWidth={1.75} />;
}

const when = (r: StoredPullRequest) => (r.state === "merged" && r.mergedAt ? `merged ${relativeTime(r.mergedAt)}` : r.state === "closed" ? `closed ${relativeTime(r.updatedAt)}` : `opened ${relativeTime(r.createdAt)}`);

export function PullRequestsTable({ page, currentBranch, repositoryUrl, newHref, hasHost }: { page: Paged<StoredPullRequest>; currentBranch: string; repositoryUrl: string | null; newHref: string | null; hasHost: boolean }) {
  const rows = page.items;
  const source = rows[0]?.source ?? null;
  return (
    <DataTable
      title="Pull requests"
      rows={rows}
      paging={page}
      rowKey={(r) => String(r.number)}
      noun={["pull request", "pull requests"]}
      meta={source ? SOURCE[source] ?? source : undefined}
      newHref={newHref}
      newLabel="New pull request"
      empty={{ icon: GitPullRequest, title: "No pull requests yet", text: hasHost ? "Open the first one with New pull request. Sync imports existing ones from the code host." : "Connect a code host and push the repository to track pull requests." }}
      action={repositoryUrl && rows.length > 0 ? <a href={`${repositoryUrl}/pulls`} target="_blank" rel="noopener noreferrer" className="hidden whitespace-nowrap text-[13px] text-secondary hover:text-foreground lg:block">View all on {SOURCE[source ?? ""] ?? "the host"}</a> : undefined}
      minWidth={760}
      columns={[
        { key: "state", label: "State", width: 8, render: (r) => <Inline><StateIcon state={r.state} draft={r.draft} /><Badge tone={r.state === "merged" ? "inverse" : r.state === "open" ? "ok" : "neutral"}>{r.state === "merged" ? "Merged" : r.state === "open" ? (r.draft ? "Draft" : "Open") : "Closed"}</Badge></Inline> },
        { key: "title", label: "Title", width: 59, render: (r) => <Inline><a href={r.url} target="_blank" rel="noopener noreferrer" className="min-w-0 truncate font-medium hover:underline underline-offset-4" title={r.title}>{r.title}</a><span className="shrink-0 font-mono text-xs text-muted-foreground">#{r.number}</span>{r.head === currentBranch && <Badge tone="ok" className="shrink-0">Current branch</Badge>}</Inline> },
        { key: "branches", label: "Branches", width: 12, hide: "md", render: (r) => <Cell mono muted title={`${r.head} → ${r.base}`}>{r.head} → {r.base}</Cell> },
        { key: "author", label: "Author", width: 9, hide: "md", render: (r) => <Cell muted title={r.author ?? undefined}>{r.author ?? "—"}</Cell> },
        { key: "when", label: "When", width: 12, hide: "sm", render: (r) => <Cell muted>{when(r)}</Cell> },
      ]}
    />
  );
}
