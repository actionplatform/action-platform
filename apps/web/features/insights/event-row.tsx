import { Activity, Cloud, GitPullRequest, Tag, Workflow } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import type { DashboardEvent } from "@/lib/insights";
import { relativeTime } from "@/lib/time";

const ICON: Record<string, typeof Activity> = { deployment: Cloud, release: Tag, pull_request: GitPullRequest, ci_run: Workflow };
const TONE: Record<string, "success" | "danger" | "neutral" | "warning" | "info"> = { verified: "success", success: "success", failure: "danger", running: "info", queued: "info", merged: "success", open: "neutral" };
const TAB: Record<string, string> = { deployment: "deployments", release: "releases", ci_run: "ci", pull_request: "activity" };

export function EventRow({ event: e, count = 1 }: { event: DashboardEvent; count?: number }) {
  const Icon = ICON[e.kind] ?? Activity;
  return (
    <li className="flex min-h-[64px] items-center gap-3 px-5 py-3">
      <span className="hidden size-9 shrink-0 items-center justify-center rounded-md border border-border text-secondary sm:flex">
        <Icon className="size-4" strokeWidth={1.75} aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-2">
          <Link href={`/projects/${e.project_id}/apps/${e.app_id}/${TAB[e.kind] ?? ""}`} className="min-w-0 truncate text-[15px] font-medium hover:underline underline-offset-4">{e.title}</Link>
          {count > 1 && <span className="shrink-0 font-mono text-[11px] text-muted-foreground">×{count}</span>}
        </div>
        <div className="truncate font-mono text-[13px] text-secondary">{e.project} / {e.app}{e.detail && <> · {e.detail}</>}</div>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1 sm:flex-row sm:items-center sm:gap-4">
        <span data-column="status" className="flex sm:w-[88px] sm:justify-center">{e.status && <Badge tone={TONE[e.status] ?? "neutral"} className="h-6 px-2.5 text-xs">{e.status}</Badge>}</span>
        <span data-column="time" className="text-right text-[13px] whitespace-nowrap text-secondary tabular-nums sm:w-[84px]" suppressHydrationWarning>{e.at ? relativeTime(e.at) : ""}</span>
      </div>
    </li>
  );
}
