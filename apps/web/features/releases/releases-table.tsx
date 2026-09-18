"use client";

import { MoreHorizontal, Plus, Tag } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Menu } from "@/components/ui/menu";
import { Pagination, usePagination } from "@/components/ui/pagination";
import { Panel, PanelHeader } from "@/components/ui/panel";
import type { Release } from "@/lib/api";
import type { StoredRelease } from "@/lib/releases";

type Row = { tag: string; version: string; name: string | null; body: string | null; url: string | null; author: string | null; sha: string | null; prerelease: boolean; draft: boolean; date: string | null; source: string };

function formatDate(d: string | null): string {
  if (!d) return "—";
  const t = new Date(d);
  return Number.isNaN(t.getTime()) ? d : t.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

const SOURCE: Record<string, string> = { github: "GitHub", gitlab: "GitLab", bitbucket: "Bitbucket", git: "Git tags" };

export function toRows(stored: StoredRelease[], fromGit: Release[], repositoryUrl: string | null): Row[] {
  if (stored.length > 0) {
    return stored.map((r) => ({ tag: r.tag, version: r.tag.split("/").pop()!.replace(/^v/, ""), name: r.name, body: r.body, url: r.url, author: r.author, sha: r.sha, prerelease: r.prerelease, draft: r.draft, date: r.publishedAt ? r.publishedAt.toISOString() : null, source: r.source }));
  }
  return fromGit.map((r) => ({ tag: r.tag, version: r.version, name: null, body: r.subject, url: repositoryUrl ? `${repositoryUrl}/releases/tag/${r.tag}` : null, author: null, sha: r.sha, prerelease: r.prerelease, draft: false, date: r.date, source: "git" }));
}

export function ReleasesTable({ stored, fromGit, repositoryUrl, newHref }: { stored: StoredRelease[]; fromGit: Release[]; repositoryUrl: string | null; newHref?: string | null }) {
  const all = toRows(stored, fromGit, repositoryUrl);
  const paging = usePagination(all);
  const rows = paging.rows;
  const offset = (paging.page - 1) * paging.per;
  const source = all[0]?.source ?? "git";
  const [changelog, setChangelog] = useState<Row | null>(null);
  const copy = (text: string) => { navigator.clipboard.writeText(text).catch(() => undefined); };
  const actions = (r: Row) => [
    ...(r.url ? [{ label: `View on ${SOURCE[r.source] ?? "the code host"}`, onSelect: () => window.open(r.url!, "_blank", "noopener") }] : []),
    { label: "Copy tag", onSelect: () => copy(r.tag) },
    ...(r.sha ? [{ label: "Copy commit SHA", onSelect: () => copy(r.sha!) }] : []),
    ...(r.body ? [{ label: "View changelog", onSelect: () => setChangelog(r) }] : []),
  ];
  const menu = (r: Row) => <Menu label={`Actions for ${r.tag}`} items={actions(r)} trigger={({ toggle, open, id }) => <Button size="icon" variant="ghost" aria-label={`Actions for ${r.tag}`} aria-haspopup="menu" aria-expanded={open} aria-controls={id} onClick={toggle}><MoreHorizontal className="size-4" strokeWidth={1.75} /></Button>} />;

  return (
    <Panel>
      <PanelHeader
        title="Releases"
        aside={
          <div className="flex items-center gap-3">
            <span className="hidden text-[13px] text-secondary sm:block">{all.length} {all.length === 1 ? "release" : "releases"} · {SOURCE[source] ?? source}</span>
            {newHref && <Link href={newHref} className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border px-3 text-sm font-medium hover:border-border-hover hover:bg-surface-hover"><Plus className="size-3.5" strokeWidth={2} /> New release</Link>}
          </div>
        }
      />
      {all.length === 0 ? (
        <div className="flex flex-col items-center px-4 py-10 text-center">
          <Tag className="size-5 text-secondary" strokeWidth={1.5} />
          <div className="mt-3 text-sm font-medium">No releases yet</div>
          <div className="text-[13px] text-secondary">Create the first one with New release, or Sync to import releases from the code host.</div>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto"><table className="hidden w-full min-w-[640px] text-sm md:table">
            <thead><tr className="text-left text-xs text-muted-foreground"><th className="px-4 py-2 font-medium">Version</th><th className="py-2 font-medium">Tag</th><th className="py-2 font-medium">Name</th><th className="py-2 font-medium">Author</th><th className="py-2 font-medium">Commit</th><th className="py-2 font-medium">Published</th><th className="py-2 pr-2" /></tr></thead>
            <tbody className="divide-y divide-border-subtle border-t border-border-subtle">
              {rows.map((r, i) => (
                <tr key={r.tag}>
                  <td className="px-4 py-2.5">
                    <span className="flex flex-wrap items-center gap-2">
                      {r.url ? <a href={r.url} target="_blank" rel="noopener noreferrer" className="font-mono font-medium hover:underline underline-offset-4">{r.version}</a> : <span className="font-mono font-medium">{r.version}</span>}
                      {offset + i === 0 && !r.draft && <Badge tone="ok">Latest</Badge>}
                      {r.prerelease && <Badge>Pre-release</Badge>}
                      {r.draft && <Badge>Draft</Badge>}
                    </span>
                  </td>
                  <td className="whitespace-nowrap py-2.5 pr-4">{repositoryUrl ? <a href={`${repositoryUrl}/releases/tag/${r.tag}`} target="_blank" rel="noopener noreferrer" className="inline-flex h-6 items-center gap-1 rounded border border-border bg-background px-1.5 font-mono text-xs hover:border-border-hover"><Tag className="size-3" strokeWidth={1.75} />{r.tag}</a> : <span className="inline-flex h-6 items-center gap-1 rounded border border-border bg-background px-1.5 font-mono text-xs"><Tag className="size-3" strokeWidth={1.75} />{r.tag}</span>}</td>
                  <td className="max-w-0 truncate py-2.5 pr-4 text-secondary" title={r.name ?? r.body ?? undefined}>{r.name ?? r.body ?? r.tag}</td>
                  <td className="whitespace-nowrap py-2.5 pr-4 text-secondary">{r.author ?? "—"}</td>
                  <td className="py-2.5 pr-4">{r.sha ? <span className="inline-flex h-6 items-center rounded border border-border bg-background px-1.5 font-mono text-xs">{r.sha}</span> : <span className="text-muted-foreground">—</span>}</td>
                  <td className="whitespace-nowrap py-2.5 pr-4 text-secondary">{formatDate(r.date)}</td>
                  <td className="py-1.5 pr-2 text-right">{menu(r)}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
          <ul className="divide-y divide-border-subtle md:hidden">
            {rows.map((r, i) => (
              <li key={r.tag} className="px-4 py-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono font-medium">{r.version}</span>
                  {offset + i === 0 && !r.draft && <Badge tone="ok">Latest</Badge>}
                  {r.prerelease && <Badge>Pre-release</Badge>}
                  <span className="ml-auto text-xs text-secondary">{formatDate(r.date)}</span>
                  {menu(r)}
                </div>
                <div className="mt-1 truncate text-[13px] text-secondary">{r.name ?? r.body ?? r.tag}</div>
                <div className="mt-1 font-mono text-xs text-muted-foreground">{r.tag}{r.sha ? ` · ${r.sha}` : ""}{r.author ? ` · ${r.author}` : ""}</div>
              </li>
            ))}
          </ul>
          <Pagination page={paging.page} pages={paging.pages} per={paging.per} total={paging.total} onPage={paging.setPage} onPer={paging.setPer} noun={["release", "releases"]} />
        </>
      )}
      <Dialog open={changelog !== null} onClose={() => setChangelog(null)} title={changelog ? `${changelog.name ?? changelog.tag}` : ""} description={changelog ? `${changelog.tag}${changelog.sha ? ` · ${changelog.sha}` : ""}${changelog.date ? ` · ${formatDate(changelog.date)}` : ""}` : undefined} className="max-w-2xl">
        {changelog && <pre className="max-h-96 overflow-auto rounded-md border border-border bg-background p-3 font-mono text-xs whitespace-pre-wrap">{changelog.body}</pre>}
      </Dialog>
    </Panel>
  );
}
