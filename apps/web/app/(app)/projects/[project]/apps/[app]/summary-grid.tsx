import { Check, CircleDashed, GitBranch, Tag, TriangleAlert, type LucideIcon } from "lucide-react";
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
  const tree = view.workingTree;
  return (
    <div className="mt-5 grid grid-cols-1 gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
      <SummaryCard label="Branch" value={view.branch || "—"} icon={GitBranch} />
      <SummaryCard label="Version" value={view.version ?? "0.0.0"} badge={view.version ? <Badge>Current</Badge> : <Badge>Unversioned</Badge>} icon={Tag} />
      <SummaryCard label="Latest tag" value={view.latestTag ?? <span className="font-sans text-sm font-normal text-secondary">No tags</span>} icon={Tag} />
      <SummaryCard
        label="Working tree"
        value={<span className="font-sans text-sm font-normal text-secondary">{tree === "clean" ? "No local changes" : tree === "dirty" ? "Uncommitted changes" : "Not a git checkout"}</span>}
        badge={
          tree === "clean" ? <Badge tone="ok" className="gap-1"><Check className="size-3" strokeWidth={2.5} /> Clean</Badge>
          : tree === "dirty" ? <Badge tone="inverse" className="gap-1"><TriangleAlert className="size-3" /> Dirty</Badge>
          : <Badge className="gap-1"><CircleDashed className="size-3" /> Unknown</Badge>
        }
        icon={CircleDashed}
      />
    </div>
  );
}
