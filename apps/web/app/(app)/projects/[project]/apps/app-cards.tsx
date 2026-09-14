import { Code2, GitBranch, Layers, Tag } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import type { AppRow } from "@/lib/api";
import { RemoveButton } from "./remove-button";

type Item = { id: string; name: string; registryId: string };

export function AppCards({ projectId, apps, rows, manage }: { projectId: string; apps: Item[]; rows: Map<string, AppRow>; manage: boolean }) {
  if (apps.length === 0) {
    return <div className="rounded-[9px] border border-dashed border-border px-5 py-10 text-center text-sm text-muted-foreground">No apps yet. Create one from a template or add a repository.</div>;
  }
  return (
    <ul className="space-y-3">
      {apps.map((a) => {
        const r = rows.get(a.registryId);
        return (
          <li key={a.id} className="min-w-0 rounded-[10px] border border-border bg-surface p-4">
            <div className="flex items-start gap-3">
              <div className="min-w-0 flex-1">
                <Link href={`/projects/${projectId}/apps/${a.id}`} className="block truncate text-[16px] font-semibold hover:underline underline-offset-4">{a.name}</Link>
                <div className="mt-1 flex min-w-0 items-center gap-2">
                  <span className="truncate font-mono text-xs text-muted-foreground">{r?.url ? r.url.replace(/^https?:\/\//, "") : "no remote"}</span>
                  {r && !r.exists && <Badge tone="bad">missing</Badge>}
                  {!r && <Badge>not on API</Badge>}
                </div>
              </div>
              {manage && <RemoveButton projectId={projectId} appId={a.id} name={a.name} repositoryUrl={r?.url || null} />}
            </div>
            <dl className="mt-4 grid grid-cols-1 gap-2 min-[360px]:grid-cols-2">
              <Meta icon={<Layers className="size-3.5" strokeWidth={1.75} />} label="Type" value={r?.type ?? "—"} />
              <Meta icon={<Code2 className="size-3.5" strokeWidth={1.75} />} label="Language" value={r?.language ?? "—"} />
              <Meta icon={<GitBranch className="size-3.5" strokeWidth={1.75} />} label="Branch" value={r?.branch ?? "—"} mono />
              <Meta icon={<Tag className="size-3.5" strokeWidth={1.75} />} label="Version" value={r?.last_version ?? "—"} mono />
            </dl>
          </li>
        );
      })}
    </ul>
  );
}

function Meta({ icon, label, value, mono }: { icon: ReactNode; label: string; value: string; mono?: boolean }) {
  return (
    <div className="min-w-0 rounded-[8px] border border-border bg-background px-3 py-2">
      <dt className="flex items-center gap-1.5 text-[11px] text-secondary">{icon}{label}</dt>
      <dd className={`mt-0.5 truncate text-sm text-foreground ${mono ? "font-mono text-[13px]" : ""}`}>{value}</dd>
    </div>
  );
}
