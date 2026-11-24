"use client";

import { Activity, ArrowRight, Boxes, CircleAlert, Cloud, ShieldCheck, Tag, TriangleAlert, Workflow } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { useScope } from "@/components/layout/scope";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel, PanelHeader } from "@/components/ui/panel";
import type { Dashboard } from "@/lib/insights";
import { DashboardSkeleton } from "./dashboard-skeleton";
import { EventRow } from "./event-row";
import { grouped } from "./events";
import { InProgressPanel } from "./in-progress";

export const LATEST = 5;
const MISSING_SHOWN = 3;

function Stat({ label, value, icon: Icon, children }: { label: string; value: number; icon: typeof Activity; children?: ReactNode }) {
  return (
    <div className="flex min-h-[136px] flex-col rounded-[10px] border border-border bg-surface p-5">
      <div className="flex items-center justify-between gap-3">
        <span className="truncate text-sm text-secondary">{label}</span>
        <Icon className="size-[18px] shrink-0 text-muted-foreground" strokeWidth={1.75} aria-hidden />
      </div>
      <div className="mt-3 text-[40px] font-semibold leading-none tabular-nums text-foreground">{value}</div>
      {children && <div className="mt-3 truncate text-sm text-secondary">{children}</div>}
    </div>
  );
}

function Failed({ count }: { count: number }) {
  return count > 0 ? <span className="text-status-bad">{count} failed</span> : <span>{count} failed</span>;
}

function More({ href, children }: { href: string; children: string }) {
  return (
    <Link href={href} className="inline-flex items-center gap-1.5 text-sm whitespace-nowrap text-secondary hover:text-foreground">
      {children}
      <ArrowRight className="size-4" strokeWidth={1.75} aria-hidden />
    </Link>
  );
}

const title = (text: string) => <span className="text-[17px]">{text}</span>;

function Attention({ label, count }: { label: string; count: number }) {
  return (
    <li className="flex min-h-[50px] items-center gap-3 px-5 py-2">
      <CircleAlert className={`size-[18px] shrink-0 ${count > 0 ? "text-status-bad" : "text-muted-foreground"}`} strokeWidth={1.75} aria-hidden />
      <span className="flex-1 text-[15px]">{label}</span>
      <span className={`text-lg font-semibold tabular-nums ${count > 0 ? "text-status-bad" : "text-secondary"}`}>{count}</span>
    </li>
  );
}

function Coverage({ data }: { data: Dashboard }) {
  const total = data.apps;
  const missing = data.without_ci;
  const covered = Math.max(0, total - missing.length);
  const pct = total ? Math.round((covered / total) * 100) : 0;
  return (
    <Panel className="rounded-[10px]">
      <PanelHeader className="h-14 px-5" title={title("CI coverage")} />
      {total === 0 ? (
        <EmptyState icon={ShieldCheck} title="No apps yet" text="Create or import an app to see whether it reads a CI." />
      ) : (
        <div className="px-5 py-5">
          <div className="text-[28px] font-semibold leading-tight tabular-nums">{covered} of {total} {total === 1 ? "app" : "apps"}</div>
          <p className="mt-1 text-sm text-secondary">{missing.length === 0 ? "All apps have CI configured" : `${missing.length} ${missing.length === 1 ? "app reads" : "apps read"} no CI yet`}</p>
          <div role="progressbar" aria-label="CI coverage" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} className="mt-4 h-2 overflow-hidden rounded-full bg-surface-hover">
            <div className="h-full rounded-full bg-status-ok" style={{ width: `${pct}%` }} />
          </div>
          {missing.length > 0 && (
            <ul className="mt-4 space-y-1.5">
              {missing.slice(0, MISSING_SHOWN).map((a) => (
                <li key={a.app_id} className="flex min-w-0 items-center gap-2 text-sm">
                  <TriangleAlert className="size-3.5 shrink-0 text-status-warn" strokeWidth={1.75} aria-hidden />
                  <Link href={`/projects/${a.project_id}/apps/${a.app_id}/ci/connect`} className="min-w-0 truncate hover:underline underline-offset-4">{a.app}</Link>
                  <span className="min-w-0 truncate text-[13px] text-secondary">{a.project}</span>
                </li>
              ))}
              {missing.length > MISSING_SHOWN && <li className="text-[13px] text-secondary">+{missing.length - MISSING_SHOWN} more</li>}
            </ul>
          )}
        </div>
      )}
    </Panel>
  );
}

export function DashboardView({ data, orgId }: { data: Dashboard; orgId: string }) {
  const { switchingTo } = useScope();
  if (switchingTo && switchingTo !== orgId) return <DashboardSkeleton />;

  const verified = data.deployments_today.verified ?? 0;
  const deployed = (data.deployments_today.success ?? 0) + verified;
  const deployFailed = data.deployments_today.failure ?? 0;
  const ciFailed = data.ci_today.failure ?? 0;
  const ciTotal = Object.values(data.ci_today).reduce((a, b) => a + b, 0);
  const latest = grouped(data.events).slice(0, LATEST);

  return (
    <div className="space-y-5 xl:space-y-6">
      <div data-testid="metrics" className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Apps" value={data.apps} icon={Boxes} />
        <Stat label="Deployments today" value={deployed} icon={Cloud}>{verified} verified · <Failed count={deployFailed} /></Stat>
        <Stat label="CI runs today" value={ciTotal} icon={Workflow}><Failed count={ciFailed} /></Stat>
        <Stat label="Releases this week" value={data.releases_week} icon={Tag} />
      </div>
      <InProgressPanel deployments={data.in_progress} />
      <div data-testid="lower" className="grid grid-cols-1 items-start gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] xl:gap-6">
        <Panel className="rounded-[10px]">
          <PanelHeader className="h-14 px-5" title={title("Latest activity")} aside={data.events.length > 0 && <More href="/dashboard/activity">View all activity</More>} />
          {latest.length === 0 ? (
            <EmptyState icon={Activity} title="Nothing yet" text="Releases, deployments, CI runs and pull requests land here as the apps sync." />
          ) : (
            <ul className="divide-y divide-border-subtle">{latest.map((g, i) => <EventRow key={`${g.event.kind}-${g.event.app_id}-${i}`} event={g.event} count={g.count} />)}</ul>
          )}
        </Panel>
        <div className="space-y-5 xl:space-y-6">
          <Panel className="rounded-[10px]">
            <PanelHeader className="h-14 px-5" title={title("Needs attention")} />
            <ul className="divide-y divide-border-subtle">
              <Attention label="Deployment failures" count={deployFailed} />
              <Attention label="CI failures" count={ciFailed} />
            </ul>
          </Panel>
          <Coverage data={data} />
        </div>
      </div>
    </div>
  );
}
