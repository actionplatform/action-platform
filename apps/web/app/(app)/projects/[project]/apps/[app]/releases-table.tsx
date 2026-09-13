import { Tag } from "lucide-react";
import { Badge } from "@/components/ui/badge";
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

export function ReleasesTable({ stored, fromGit, repositoryUrl }: { stored: StoredRelease[]; fromGit: Release[]; repositoryUrl: string | null }) {
  const rows = toRows(stored, fromGit, repositoryUrl);
  const source = rows[0]?.source ?? "git";

  return (
    <Panel>
      <PanelHeader title="All releases" aside={<span className="text-[13px] text-secondary">{rows.length} {rows.length === 1 ? "release" : "releases"} · {SOURCE[source] ?? source}</span>} />
      {rows.length === 0 ? (
        <div className="flex flex-col items-center px-4 py-10 text-center">
          <Tag className="size-5 text-secondary" strokeWidth={1.5} />
          <div className="mt-3 text-sm font-medium">No releases yet</div>
          <div className="text-[13px] text-secondary">Create the first one above, or Sync to import releases from the code host.</div>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto"><table className="hidden w-full min-w-[640px] text-sm md:table">
            <thead><tr className="text-left text-xs text-muted-foreground"><th className="px-4 py-2 font-medium">Version</th><th className="py-2 font-medium">Tag</th><th className="py-2 font-medium">Name</th><th className="py-2 font-medium">Author</th><th className="py-2 font-medium">Commit</th><th className="py-2 pr-4 font-medium">Published</th></tr></thead>
            <tbody className="divide-y divide-border-subtle border-t border-border-subtle">
              {rows.map((r, i) => (
                <tr key={r.tag}>
                  <td className="px-4 py-2.5">
                    <span className="flex flex-wrap items-center gap-2">
                      {r.url ? <a href={r.url} target="_blank" rel="noopener noreferrer" className="font-mono font-medium hover:underline underline-offset-4">{r.version}</a> : <span className="font-mono font-medium">{r.version}</span>}
                      {i === 0 && !r.draft && <Badge tone="ok">Latest</Badge>}
                      {r.prerelease && <Badge>Pre-release</Badge>}
                      {r.draft && <Badge>Draft</Badge>}
                    </span>
                  </td>
                  <td className="whitespace-nowrap py-2.5 pr-4">{repositoryUrl ? <a href={`${repositoryUrl}/releases/tag/${r.tag}`} target="_blank" rel="noopener noreferrer" className="inline-flex h-6 items-center gap-1 rounded border border-border bg-background px-1.5 font-mono text-xs hover:border-border-hover"><Tag className="size-3" strokeWidth={1.75} />{r.tag}</a> : <span className="inline-flex h-6 items-center gap-1 rounded border border-border bg-background px-1.5 font-mono text-xs"><Tag className="size-3" strokeWidth={1.75} />{r.tag}</span>}</td>
                  <td className="max-w-0 truncate py-2.5 pr-4 text-secondary" title={r.body ?? undefined}>{r.name ?? r.body ?? r.tag}</td>
                  <td className="whitespace-nowrap py-2.5 pr-4 text-secondary">{r.author ?? "—"}</td>
                  <td className="py-2.5 pr-4">{r.sha ? <span className="inline-flex h-6 items-center rounded border border-border bg-background px-1.5 font-mono text-xs">{r.sha}</span> : <span className="text-muted-foreground">—</span>}</td>
                  <td className="whitespace-nowrap py-2.5 pr-4 text-secondary">{formatDate(r.date)}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
          <ul className="divide-y divide-border-subtle md:hidden">
            {rows.map((r, i) => (
              <li key={r.tag} className="px-4 py-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono font-medium">{r.version}</span>
                  {i === 0 && !r.draft && <Badge tone="ok">Latest</Badge>}
                  {r.prerelease && <Badge>Pre-release</Badge>}
                  <span className="ml-auto text-xs text-secondary">{formatDate(r.date)}</span>
                </div>
                <div className="mt-1 truncate text-[13px] text-secondary">{r.name ?? r.body ?? r.tag}</div>
                <div className="mt-1 font-mono text-xs text-muted-foreground">{r.tag}{r.sha ? ` · ${r.sha}` : ""}{r.author ? ` · ${r.author}` : ""}</div>
              </li>
            ))}
          </ul>
        </>
      )}
    </Panel>
  );
}
