import { ArrowRight, Cloud, GitBranch, Tag, TriangleAlert, type LucideIcon } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import type { AppView } from "./model";
import { NameChips } from "@/components/ui/name-chips";
import { targetNamesOf } from "@/features/deployments";

export function SummaryCard({ label, value, badge, icon: Icon }: { label: string; value: ReactNode; badge?: ReactNode; icon: LucideIcon }) {
  return (
    <div className="flex h-[104px] min-w-0 flex-col overflow-hidden rounded-lg border border-border bg-surface px-[18px] py-[17px]">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        {label}
        <Icon className="size-4" strokeWidth={1.75} />
      </div>
      <div className="mt-auto flex min-w-0 items-center gap-2 pt-3">
        <div className="min-w-0 truncate font-mono text-lg font-semibold leading-6" title={typeof value === "string" ? value : undefined}>{value}</div>
        {badge && <span className="shrink-0">{badge}</span>}
      </div>
    </div>
  );
}

export function SummaryGrid({ view }: { view: AppView }) {
  const targets = targetNamesOf(view.deploy);
  return (
    <div className="mt-5 grid grid-cols-1 gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
      <SummaryCard label="Branch" value={view.branch || "—"} icon={GitBranch} />
      <SummaryCard label="Version" value={view.version ?? "0.0.0"} badge={view.version ? <Badge>Current</Badge> : <Badge>Unversioned</Badge>} icon={Tag} />
      <SummaryCard label="Latest tag" value={view.latestTag ?? <span className="font-sans text-sm font-normal text-secondary">No tags</span>} icon={Tag} />
      <SummaryCard
        label="Deploy"
        value={targets.length ? <NameChips names={targets} noun="deploy target" href={`/projects/${view.projectId}/apps/${view.appId}/settings?tab=deploy`} /> : <span className="font-sans text-sm font-normal text-secondary">Not configured</span>}
        badge={targets.length ? <Badge tone="ok">Configured</Badge> : undefined}
        icon={Cloud}
      />
    </div>
  );
}

export function PendingChangesBanner({ view, base }: { view: AppView; base: string }) {
  const pending = view.changes.length;
  if (pending === 0) return null;
  return (
    <Link href={`${base}/settings?tab=deploy`} className="mt-4 flex items-center gap-3 rounded-lg border border-border bg-surface px-[18px] py-3 text-sm transition-colors hover:border-border-hover hover:bg-surface-hover">
      <TriangleAlert className="size-4 shrink-0 text-secondary" strokeWidth={1.75} />
      <span><span className="font-medium">{pending} {pending === 1 ? "file" : "files"} to commit</span> <span className="text-secondary">— changes made in Settings are waiting on a branch and a pull request.</span></span>
      <ArrowRight className="ml-auto size-4 shrink-0 text-secondary" strokeWidth={1.75} />
    </Link>
  );
}
