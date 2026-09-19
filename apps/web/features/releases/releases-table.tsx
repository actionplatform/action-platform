"use client";

import { MoreHorizontal, Tag } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Cell, DataTable, Inline } from "@/components/ui/data-table";
import { Dialog } from "@/components/ui/dialog";
import { Menu } from "@/components/ui/menu";
import type { Paged } from "@/lib/page";
import type { StoredRelease, Verdict } from "@/lib/releases";
import { ReadinessBadges } from "@/features/readiness";

type Row = { tag: string; component: string | null; version: string; name: string | null; body: string | null; url: string | null; author: string | null; sha: string | null; prerelease: boolean; draft: boolean; date: string | null; source: string; readiness: Record<string, Verdict> };

function formatDate(d: string | null): string {
  if (!d) return "—";
  const t = new Date(d);
  return Number.isNaN(t.getTime()) ? d : t.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

const SOURCE: Record<string, string> = { github: "GitHub", gitlab: "GitLab", bitbucket: "Bitbucket", git: "Git tags", platform: "Platform" };

export function toRows(stored: StoredRelease[], repositoryUrl: string | null): Row[] {
  return stored.map((r) => ({ tag: r.tag, component: r.tag.includes("/") ? r.tag.slice(0, r.tag.lastIndexOf("/")) : null, version: r.version || r.tag.split("/").pop()!.replace(/^v/, ""), name: r.name, body: r.body, url: r.url ?? (repositoryUrl ? `${repositoryUrl}/releases/tag/${r.tag}` : null), author: r.author, sha: r.sha, prerelease: r.prerelease, draft: r.draft, date: r.publishedAt ? r.publishedAt.toISOString() : null, source: r.source, readiness: r.readiness }));
}

export function ReleasesTable({ page, repositoryUrl, newHref, base }: { page: Paged<StoredRelease>; repositoryUrl: string | null; newHref?: string | null; base?: string }) {
  const router = useRouter();
  const rows = toRows(page.items, repositoryUrl);
  const latest = new Set(rows.filter((r, i) => !r.draft && rows.findIndex((o) => !o.draft && o.component === r.component) === i).map((r) => r.tag));
  const source = rows[0]?.source ?? "git";
  const [changelog, setChangelog] = useState<Row | null>(null);
  const copy = (text: string) => { navigator.clipboard.writeText(text).catch(() => undefined); };
  const actions = (r: Row) => [
    ...(base ? [{ label: "Timeline & readiness", onSelect: () => router.push(`${base}/releases/${encodeURIComponent(r.tag)}`) }] : []),
    ...(r.url ? [{ label: `View on ${SOURCE[r.source] ?? "the code host"}`, onSelect: () => window.open(r.url!, "_blank", "noopener") }] : []),
    { label: "Copy tag", onSelect: () => copy(r.tag) },
    ...(r.sha ? [{ label: "Copy commit SHA", onSelect: () => copy(r.sha!) }] : []),
    ...(r.body ? [{ label: "View changelog", onSelect: () => setChangelog(r) }] : []),
  ];
  const tagChip = (r: Row) => {
    const inner = <><Tag className="size-3 shrink-0" strokeWidth={1.75} /><span className="truncate">{r.tag}</span></>;
    const cls = "inline-flex h-6 max-w-full items-center gap-1 rounded border border-border bg-background px-1.5 font-mono text-xs";
    return repositoryUrl ? <a href={`${repositoryUrl}/releases/tag/${r.tag}`} target="_blank" rel="noopener noreferrer" className={`${cls} hover:border-border-hover`} title={r.tag}>{inner}</a> : <span className={cls} title={r.tag}>{inner}</span>;
  };

  return (
    <>
      <DataTable
        title="Releases"
        rows={rows}
        paging={page}
        rowKey={(r) => r.tag}
        noun={["release", "releases"]}
        meta={rows.length > 0 ? SOURCE[source] ?? source : undefined}
        newHref={newHref}
        newLabel="New release"
        empty={{ icon: Tag, title: "No releases yet", text: "Create the first one with New release, or Sync to import releases from the code host." }}
        minWidth={800}
        columns={[
          { key: "version", label: "Version", width: 28, render: (r) => <Inline>{base ? <Link href={`${base}/releases/${encodeURIComponent(r.tag)}`} className="font-mono font-medium hover:underline underline-offset-4">{r.version}</Link> : r.url ? <a href={r.url} target="_blank" rel="noopener noreferrer" className="font-mono font-medium hover:underline underline-offset-4">{r.version}</a> : <span className="font-mono font-medium">{r.version}</span>}{r.component && <Badge className="shrink-0">{r.component}</Badge>}{latest.has(r.tag) && <Badge tone="ok" className="shrink-0">Latest</Badge>}{r.prerelease && <Badge className="shrink-0">Pre-release</Badge>}{r.draft && <Badge className="shrink-0">Draft</Badge>}</Inline> },
          { key: "tag", label: "Tag", width: 14, hide: "sm", render: tagChip },
          { key: "readiness", label: "Ready", width: 16, render: (r) => <ReadinessBadges readiness={r.readiness} compact /> },
          { key: "author", label: "By", width: 14, hide: "md", render: (r) => <Cell muted title={r.author ?? undefined}>{r.author ?? "—"}</Cell> },
          { key: "sha", label: "Commit", width: 10, hide: "md", render: (r) => r.sha ? <span className="inline-flex h-6 items-center rounded border border-border bg-background px-1.5 font-mono text-xs">{r.sha.slice(0, 7)}</span> : <Cell muted>—</Cell> },
          { key: "date", label: "Published", width: 14, hide: "sm", render: (r) => <Cell muted>{formatDate(r.date)}</Cell> },
          { key: "actions", label: "", width: 4, align: "right", render: (r) => <Menu label={`Actions for ${r.tag}`} items={actions(r)} trigger={({ toggle, open, id }) => <Button size="icon" variant="ghost" aria-label={`Actions for ${r.tag}`} aria-haspopup="menu" aria-expanded={open} aria-controls={id} onClick={toggle}><MoreHorizontal className="size-4" strokeWidth={1.75} /></Button>} /> },
        ]}
      />
      <Dialog open={changelog !== null} onClose={() => setChangelog(null)} title={changelog ? `${changelog.name ?? changelog.tag}` : ""} description={changelog ? `${changelog.tag}${changelog.sha ? ` · ${changelog.sha}` : ""}${changelog.date ? ` · ${formatDate(changelog.date)}` : ""}` : undefined} className="max-w-2xl">
        {changelog && <pre className="max-h-96 overflow-auto rounded-md border border-border bg-background p-3 font-mono text-xs whitespace-pre-wrap">{changelog.body}</pre>}
      </Dialog>
    </>
  );
}
