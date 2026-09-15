import { ArrowRight, Cloud, GitBranch, Tag, TriangleAlert, type LucideIcon } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import type { AppView } from "./model";

function SummaryCard({ label, value, badge, icon: Icon }: { label: string; value: ReactNode; badge?: ReactNode; icon: LucideIcon }) {
  return (
    <div className="flex min-h-[104px] flex-col rounded-lg border border-border bg-surface px-[18px] py-[17px]">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        {label}
        <Icon className="size-4" strokeWidth={1.75} />
      </div>
      <div className="mt-auto flex flex-wrap items-center gap-2 pt-3">
        <span className="font-mono text-lg font-semibold leading-6">{value}</span>
        {badge}
      </div>
    </div>
  );
}

export function SummaryGrid({ view }: { view: AppView }) {
  const target = typeof view.deploy.target === "string" ? String(view.deploy.target) : null;
  return (
    <div className="mt-5 grid grid-cols-1 gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
      <SummaryCard label="Branch" value={view.branch || "—"} icon={GitBranch} />
      <SummaryCard label="Version" value={view.version ?? "0.0.0"} badge={view.version ? <Badge>Current</Badge> : <Badge>Unversioned</Badge>} icon={Tag} />
      <SummaryCard label="Latest tag" value={view.latestTag ?? <span className="font-sans text-sm font-normal text-secondary">No tags</span>} icon={Tag} />
      <SummaryCard
        label="Deploy"
        value={target ?? <span className="font-sans text-sm font-normal text-secondary">Not configured</span>}
        badge={target ? <Badge tone="ok">Configured</Badge> : undefined}
        icon={Cloud}
      />
    </div>
  );
}

export function PendingChangesBanner({ view, base }: { view: AppView; base: string }) {
  const pending = view.changes.length;
  if (pending === 0) return null;
  return (
    <Link href={`${base}/configuration`} className="mt-4 flex items-center gap-3 rounded-lg border border-border bg-surface px-[18px] py-3 text-sm transition-colors hover:border-border-hover hover:bg-surface-hover">
      <TriangleAlert className="size-4 shrink-0 text-secondary" strokeWidth={1.75} />
      <span><span className="font-medium">{pending} {pending === 1 ? "file" : "files"} to commit</span> <span className="text-secondary">— changes made in Configuration are waiting on a branch and a pull request.</span></span>
      <ArrowRight className="ml-auto size-4 shrink-0 text-secondary" strokeWidth={1.75} />
    </Link>
  );
}
