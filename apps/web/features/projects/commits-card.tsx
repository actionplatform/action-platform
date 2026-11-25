import { GitCommitHorizontal } from "lucide-react";
import { Cell } from "@/components/ui/data-table";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { TBody, Td, Th, Tr } from "@/components/ui/table";
import type { Commit } from "@/lib/api";

function formatDate(d: string): string {
  const t = new Date(d);
  return Number.isNaN(t.getTime()) ? d : t.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function CommitsCard({ commits, repositoryUrl, limit = 8, title = "Recent commits" }: { commits: Commit[]; repositoryUrl: string | null; limit?: number; title?: string }) {
  const rows = commits.slice(0, limit);
  const hashLink = (sha: string) => (repositoryUrl ? `${repositoryUrl}/commit/${sha}` : null);

  return (
    <Panel>
      <PanelHeader title={title} />
      {rows.length === 0 ? (
        <div className="flex flex-col items-center px-4 py-10 text-center">
          <GitCommitHorizontal className="size-5 text-secondary" strokeWidth={1.5} />
          <div className="mt-3 text-sm font-medium">No commits found</div>
          <div className="text-[13px] text-secondary">Sync the repository to load its commit history.</div>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto"><table className="hidden w-full min-w-[640px] table-fixed text-sm md:table">
            <colgroup><col className="w-[120px]" /><col /><col className="w-[18%]" /><col className="w-[128px]" /></colgroup>
            <thead><tr><Th>Commit</Th><Th>Message</Th><Th>Author</Th><Th>Date</Th></tr></thead>
            <TBody>
              {rows.map((c) => (
                <Tr key={c.sha}>
                  <Td><Hash sha={c.sha} href={hashLink(c.sha)} /></Td>
                  <Td><Cell>{c.subject}</Cell></Td>
                  <Td><Cell muted>{c.author}</Cell></Td>
                  <Td className="whitespace-nowrap text-secondary" suppressHydrationWarning>{formatDate(c.date)}</Td>
                </Tr>
              ))}
            </TBody>
          </table></div>
          <ul className="divide-y divide-border-subtle md:hidden">
            {rows.map((c) => (
              <li key={c.sha} className="px-4 py-3 text-sm">
                <div className="flex items-center gap-2 text-xs text-secondary" suppressHydrationWarning><Hash sha={c.sha} href={hashLink(c.sha)} /> · {formatDate(c.date)}</div>
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
