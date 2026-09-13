import { GitBranch, Tag } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { cn } from "@/lib/utils";
import type { Branch } from "@/lib/api";

export function RefsCard({ branches, tags, repositoryUrl, base, limit = 5, fill = false, showTags = true }: { branches: Branch[]; tags: string[]; repositoryUrl: string | null; base: string; limit?: number; fill?: boolean; showTags?: boolean }) {
  const shown = fill ? branches : branches.slice(0, limit);
  const shownTags = fill ? tags : tags.slice(0, limit);
  return (
    <Panel className={cn(fill && "flex h-full flex-col")}>
      <PanelHeader title="Git references" aside={fill ? <span className="text-[13px] text-secondary">{branches.length} {branches.length === 1 ? "branch" : "branches"}{showTags ? ` · ${tags.length} ${tags.length === 1 ? "tag" : "tags"}` : ""}</span> : undefined} />
      <div className={cn("px-4 py-3", fill && "min-h-0 flex-1 overflow-auto")}>
        <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground"><GitBranch className="size-3.5" strokeWidth={1.75} /> Branches</div>
        {shown.length === 0 ? (
          <div className="text-sm text-secondary">No branches yet</div>
        ) : (
          <ul className="space-y-1.5">
            {shown.map((b) => (
              <li key={b.name} className="flex items-center justify-between gap-3 text-sm">
                <span className="truncate font-mono text-[13px]">{b.name}</span>
                {b.protected ? <Badge>Protected</Badge> : b.problem ? <Badge tone="inverse">Not git-flow</Badge> : b.kind ? <Badge>{b.kind}</Badge> : null}
              </li>
            ))}
          </ul>
        )}
        {!fill && branches.length > limit && <Link href={`${base}/releases`} className="mt-2 inline-block text-[13px] text-secondary hover:text-foreground">View all branches</Link>}
      </div>
      {showTags && (
      <div className={cn("border-t border-border px-4 py-3", fill && "min-h-0 flex-1 overflow-auto")}>
        <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground"><Tag className="size-3.5" strokeWidth={1.75} /> Tags</div>
        {tags.length === 0 ? (
          <div className="text-sm text-secondary">No tags created yet</div>
        ) : (
          <ul className="space-y-1.5">
            {shownTags.map((t, i) => (
              <li key={t} className="flex items-center justify-between gap-3 text-sm">
                {repositoryUrl ? <a href={`${repositoryUrl}/releases/tag/${t}`} target="_blank" rel="noopener noreferrer" className="truncate font-mono text-[13px] hover:underline underline-offset-4">{t}</a> : <span className="truncate font-mono text-[13px]">{t}</span>}
                {i === 0 && <Badge tone="ok">Latest</Badge>}
              </li>
            ))}
          </ul>
        )}
      </div>
      )}
    </Panel>
  );
}
