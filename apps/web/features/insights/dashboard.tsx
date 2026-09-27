import { Activity, ArrowRight, Boxes, Cloud, GitPullRequest, ShieldCheck, Tag, TriangleAlert, Workflow } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel, PanelHeader } from "@/components/ui/panel";
import type { Dashboard, DashboardEvent } from "@/lib/insights";
import { relativeTime } from "@/lib/time";

export const LATEST = 5;
const APPS_SHOWN = 5;

function Stat({ label, value, hint, icon: Icon, tone }: { label: string; value: number; hint?: string; icon: typeof Activity; tone?: "ok" | "bad" }) {
  return (
    <div className="flex min-h-[100px] flex-col rounded-lg border border-border bg-surface p-4 sm:min-h-[112px] sm:p-5">
      <div className="flex items-center justify-between gap-3">
        <span className="truncate text-[13px] text-secondary">{label}</span>
        <Icon className="size-4 shrink-0 text-muted-foreground" strokeWidth={1.75} aria-hidden />
      </div>
      <div className={`mt-3 text-[32px] font-semibold leading-none tabular-nums ${tone === "bad" ? "text-status-bad" : tone === "ok" ? "text-status-ok" : ""}`}>{value}</div>
      {hint && <div className="mt-2 truncate text-[13px] text-secondary">{hint}</div>}
    </div>
  );
}

const ICON: Record<string, typeof Activity> = { deployment: Cloud, release: Tag, pull_request: GitPullRequest, ci_run: Workflow };
const TONE: Record<string, "success" | "danger" | "neutral" | "warning"> = { verified: "success", success: "success", failure: "danger", running: "warning", merged: "success", open: "neutral" };
const TAB: Record<string, string> = { deployment: "deployments", release: "releases", ci_run: "ci", pull_request: "activity" };

export type EventGroup = { event: DashboardEvent; count: number };

export function grouped(events: DashboardEvent[]): EventGroup[] {
  const out: EventGroup[] = [];
  for (const e of events) {
    const last = out[out.length - 1];
    if (last && last.event.kind === e.kind && last.event.app_id === e.app_id && last.event.title === e.title && last.event.status === e.status) last.count += 1;
    else out.push({ event: e, count: 1 });
  }
  return out;
}

export function EventRow({ event: e, count = 1 }: { event: DashboardEvent; count?: number }) {
  const Icon = ICON[e.kind] ?? Activity;
  return (
    <li className="flex min-h-[60px] items-center gap-3 px-4 py-2.5 sm:px-5">
      <span className="hidden size-8 shrink-0 items-center justify-center rounded-md border border-border-subtle text-secondary sm:flex">
        <Icon className="size-4" strokeWidth={1.75} aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-2">
          <Link href={`/projects/${e.project_id}/apps/${e.app_id}/${TAB[e.kind] ?? ""}`} className="min-w-0 truncate text-sm font-medium hover:underline underline-offset-4">{e.title}</Link>
          {count > 1 && <span className="shrink-0 font-mono text-[11px] text-muted-foreground">×{count}</span>}
        </div>
        <div className="truncate text-xs text-secondary">{e.project} / {e.app}{e.detail && <> · <span className="font-mono">{e.detail}</span></>}</div>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1 sm:flex-row sm:items-center sm:gap-3">
        {e.status && <Badge tone={TONE[e.status] ?? "neutral"} className="h-5 px-2 text-[11px]">{e.status}</Badge>}
        <span className="text-right text-xs whitespace-nowrap text-secondary tabular-nums sm:w-20" suppressHydrationWarning>{e.at ? relativeTime(e.at) : ""}</span>
      </div>
    </li>
  );
}

function More({ href, children }: { href: string; children: string }) {
  return (
    <Link href={href} className="inline-flex items-center gap-1 text-[13px] whitespace-nowrap text-secondary hover:text-foreground">
      {children}
      <ArrowRight className="size-3.5" strokeWidth={1.75} aria-hidden />
    </Link>
  );
}

export function DashboardView({ data }: { data: Dashboard }) {
  const deployed = (data.deployments_today.success ?? 0) + (data.deployments_today.verified ?? 0);
  const deployFailed = data.deployments_today.failure ?? 0;
  const ciFailed = data.ci_today.failure ?? 0;
  const ciTotal = Object.values(data.ci_today).reduce((a, b) => a + b, 0);
  const latest = grouped(data.events).slice(0, LATEST);
  const apps = data.without_ci.slice(0, APPS_SHOWN);
  const hidden = data.without_ci.length - apps.length;
  const deployHint = `${data.deployments_today.verified ?? 0} verified${deployFailed > 0 ? ` · ${deployFailed} failed` : ""}`;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4 xl:gap-5">
        <Stat label="Apps" value={data.apps} icon={Boxes} />
        <Stat label="Deployments today" value={deployed} hint={deployHint} icon={Cloud} tone={deployFailed > 0 ? "bad" : undefined} />
        <Stat label="CI runs today" value={ciTotal} hint={`${ciFailed} failed`} icon={Workflow} tone={ciFailed > 0 ? "bad" : undefined} />
        <Stat label="Releases this week" value={data.releases_week} icon={Tag} />
      </div>
      <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <Panel>
          <PanelHeader className="h-14 px-5" title="Latest activity" aside={data.events.length > 0 && <More href="/dashboard/activity">View all activity</More>} />
          {latest.length === 0 ? (
            <EmptyState icon={Activity} title="Nothing yet" text="Releases, deployments, CI runs and pull requests land here as the apps sync." />
          ) : (
            <ul className="divide-y divide-border-subtle">{latest.map((g, i) => <EventRow key={`${g.event.kind}-${g.event.app_id}-${i}`} event={g.event} count={g.count} />)}</ul>
          )}
        </Panel>
        <Panel>
          <PanelHeader className="h-14 px-5" title="Apps without CI" aside={<Badge tone={data.without_ci.length ? "warning" : "success"} className="h-5 px-2 text-[11px] tabular-nums">{data.without_ci.length}</Badge>} />
          {apps.length === 0 ? (
            <EmptyState icon={ShieldCheck} title="Every app reads a CI" />
          ) : (
            <>
              <ul className="divide-y divide-border-subtle">
                {apps.map((a) => (
                  <li key={a.app_id} className="flex min-h-[60px] items-center gap-3 px-5 py-2.5">
                    <TriangleAlert className="size-4 shrink-0 text-status-warn" strokeWidth={1.75} aria-hidden />
                    <div className="min-w-0 flex-1">
                      <Link href={`/projects/${a.project_id}/apps/${a.app_id}/ci/connect`} className="block truncate text-sm font-medium hover:underline underline-offset-4">{a.app}</Link>
                      <div className="truncate text-xs text-secondary">{a.project}</div>
                    </div>
                  </li>
                ))}
              </ul>
              <div className="flex min-h-12 items-center justify-between gap-3 border-t border-border-subtle px-5 py-2">
                <span className="text-[13px] text-secondary">{hidden > 0 ? `+${hidden} more ${hidden === 1 ? "app" : "apps"}` : ""}</span>
                <More href="/projects">View all apps</More>
              </div>
            </>
          )}
        </Panel>
      </div>
    </div>
  );
}
