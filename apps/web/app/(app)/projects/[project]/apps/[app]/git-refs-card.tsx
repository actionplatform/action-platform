"use client";

import { ExternalLink, GitBranch, MoreHorizontal } from "lucide-react";
import { siBitbucket, siGithub, siGitlab } from "simple-icons";
import { Badge } from "@/components/ui/badge";
import { BrandIcon } from "@/components/ui/brand-icon";
import { Button } from "@/components/ui/button";
import { Menu } from "@/components/ui/menu";
import { Panel, PanelHeader } from "@/components/ui/panel";
import type { Branch } from "@/lib/api";
import { relativeTime } from "@/lib/time";

const ICONS = { github: siGithub, gitlab: siGitlab, bitbucket: siBitbucket } as const;
const HOSTS = { github: "GitHub", gitlab: "GitLab", bitbucket: "Bitbucket" } as const;

function branchUrl(repositoryUrl: string | null, kind: string | null, name: string): string | null {
  if (!repositoryUrl) return null;
  if (kind === "gitlab") return `${repositoryUrl}/-/tree/${name}`;
  if (kind === "bitbucket") return `${repositoryUrl}/branch/${name}`;
  return `${repositoryUrl}/tree/${name}`;
}

function commitUrl(repositoryUrl: string | null, kind: string | null, sha: string): string | null {
  if (!repositoryUrl) return null;
  if (kind === "gitlab") return `${repositoryUrl}/-/commit/${sha}`;
  if (kind === "bitbucket") return `${repositoryUrl}/commits/${sha}`;
  return `${repositoryUrl}/commit/${sha}`;
}

export function GitRefsCard({ branches, repository, repositoryUrl, sourceKind, defaultBranch }: { branches: Branch[]; repository: string | null; repositoryUrl: string | null; sourceKind: string | null; defaultBranch: string | null }) {
  const kind = sourceKind && sourceKind in ICONS ? (sourceKind as keyof typeof ICONS) : null;
  const rows = branches.filter((b) => b.name !== "origin" && b.name !== "HEAD");
  const copy = (text: string) => { navigator.clipboard.writeText(text).catch(() => undefined); };

  return (
    <Panel>
      <PanelHeader title="Git references" aside={<span className="text-[13px] text-secondary">{rows.length} {rows.length === 1 ? "branch" : "branches"}</span>} />
      {repository && (
        <div className="flex items-start gap-3 border-b border-border-subtle px-4 py-3">
          {kind ? <BrandIcon icon={ICONS[kind]} mono className="mt-0.5 size-4 text-secondary" /> : <GitBranch className="mt-0.5 size-4 text-secondary" strokeWidth={1.75} />}
          <div className="min-w-0 flex-1">
            <div className="truncate font-mono text-[13px]" title={repository}>{repository}</div>
            <div className="text-[13px] text-secondary">Source repository{kind ? ` on ${HOSTS[kind]}` : ""}.</div>
          </div>
          {repositoryUrl && <a href={repositoryUrl} target="_blank" rel="noopener noreferrer" className="inline-flex shrink-0 items-center gap-1 text-[13px] text-secondary hover:text-foreground focus-visible:outline-none focus-visible:text-foreground">View repository <ExternalLink className="size-3" strokeWidth={1.75} /></a>}
        </div>
      )}
      {rows.length === 0 ? (
        <div className="px-4 py-6 text-center text-sm text-secondary">No branches yet</div>
      ) : (
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs text-muted-foreground"><th className="px-4 py-2 font-medium">Branch</th><th className="py-2 font-medium">Latest commit</th><th className="py-2 font-medium">Updated</th><th className="py-2 pr-2" /></tr></thead>
          <tbody className="divide-y divide-border-subtle border-t border-border-subtle">
            {rows.map((b) => {
              const url = branchUrl(repositoryUrl, sourceKind, b.name);
              const sha = b.sha ?? null;
              return (
                <tr key={b.name}>
                  <td className="max-w-0 px-4 py-2">
                    <div className="flex items-center gap-2">
                      <span className="truncate font-mono text-[13px]" title={b.name}>{b.name}</span>
                      {b.name === defaultBranch && <Badge>Default</Badge>}
                      {b.protected && <Badge>Protected</Badge>}
                      {!b.protected && b.problem && <Badge tone="inverse">Not git-flow</Badge>}
                    </div>
                  </td>
                  <td className="whitespace-nowrap py-2 pr-3">{sha ? (commitUrl(repositoryUrl, sourceKind, sha) ? <a href={commitUrl(repositoryUrl, sourceKind, sha)!} target="_blank" rel="noopener noreferrer" className="inline-flex h-6 items-center rounded border border-border bg-background px-1.5 font-mono text-xs hover:border-border-hover">{sha}</a> : <span className="font-mono text-xs">{sha}</span>) : <span className="text-muted-foreground">—</span>}</td>
                  <td className="whitespace-nowrap py-2 pr-2 text-[13px] text-secondary" title={b.date}>{relativeTime(b.date)}</td>
                  <td className="py-1 pr-2 text-right">
                    <Menu
                      label={`Actions for ${b.name}`}
                      items={[
                        ...(url ? [{ label: `View on ${kind ? HOSTS[kind] : "the code host"}`, onSelect: () => window.open(url, "_blank", "noopener") }] : []),
                        { label: "Copy branch name", onSelect: () => copy(b.name) },
                        ...(sha ? [{ label: "Copy commit SHA", onSelect: () => copy(sha) }] : []),
                      ]}
                      trigger={({ toggle, open, id }) => <Button size="icon" variant="ghost" aria-label={`Actions for ${b.name}`} aria-haspopup="menu" aria-expanded={open} aria-controls={id} onClick={toggle}><MoreHorizontal className="size-4" strokeWidth={1.75} /></Button>}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </Panel>
  );
}
