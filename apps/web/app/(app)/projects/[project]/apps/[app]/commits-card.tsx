import { GitCommitHorizontal } from "lucide-react";
import Link from "next/link";
import { Panel, PanelHeader } from "@/components/ui/panel";
import type { Commit } from "@/lib/api";

function formatDate(d: string): string {
  const t = new Date(d);
  return Number.isNaN(t.getTime()) ? d : t.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function CommitsCard({ commits, repositoryUrl, base, limit = 8, title = "Recent commits" }: { commits: Commit[]; repositoryUrl: string | null; base: string; limit?: number; title?: string }) {
  const rows = commits.slice(0, limit);
  const hashLink = (sha: string) => (repositoryUrl ? `${repositoryUrl}/commit/${sha}` : null);

  return (
    <Panel>
      <PanelHeader title={title} aside={commits.length > limit ? <Link href={`${base}/activity`} className="text-[13px] text-secondary hover:text-foreground focus-visible:outline-none focus-visible:text-foreground">View all</Link> : null} />
      {rows.length === 0 ? (
        <div className="flex flex-col items-center px-4 py-10 text-center">
          <GitCommitHorizontal className="size-5 text-secondary" strokeWidth={1.5} />
          <div className="mt-3 text-sm font-medium">No commits found</div>
          <div className="text-[13px] text-secondary">Sync the repository to load its commit history.</div>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto"><table className="hidden w-full min-w-[640px] text-sm md:table">
            <thead><tr className="text-left text-xs text-muted-foreground"><th className="px-4 py-2 font-medium">Commit</th><th className="py-2 font-medium">Message</th><th className="py-2 font-medium">Author</th><th className="py-2 pr-4 font-medium">Date</th></tr></thead>
            <tbody className="divide-y divide-border-subtle border-t border-border-subtle">
              {rows.map((c) => (
                <tr key={c.sha}>
                  <td className="px-4 py-2.5"><Hash sha={c.sha} href={hashLink(c.sha)} /></td>
                  <td className="max-w-0 truncate py-2.5 pr-4">{c.subject}</td>
                  <td className="whitespace-nowrap py-2.5 pr-4 text-secondary">{c.author}</td>
                  <td className="whitespace-nowrap py-2.5 pr-4 text-secondary">{formatDate(c.date)}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
          <ul className="divide-y divide-border-subtle md:hidden">
            {rows.map((c) => (
              <li key={c.sha} className="px-4 py-3 text-sm">
                <div className="flex items-center gap-2 text-xs text-secondary"><Hash sha={c.sha} href={hashLink(c.sha)} /> · {formatDate(c.date)}</div>
                <div className="mt-1">{c.subject}</div>
                <div className="text-[13px] text-secondary">{c.author}</div>
              </li>
            ))}
          </ul>
        </>
      )}
    </Panel>
  );
}

function Hash({ sha, href }: { sha: string; href: string | null }) {
  const cls = "inline-flex h-6 items-center rounded border border-border bg-background px-1.5 font-mono text-xs";
  return href ? <a href={href} target="_blank" rel="noopener noreferrer" className={`${cls} hover:border-border-hover hover:text-foreground`}>{sha}</a> : <span className={cls}>{sha}</span>;
}
