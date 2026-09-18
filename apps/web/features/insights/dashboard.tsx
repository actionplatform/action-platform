import { Activity, Cloud, GitPullRequest, Rocket, ShieldCheck, Tag, TriangleAlert, Workflow } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel, PanelHeader } from "@/components/ui/panel";
import type { Dashboard, DashboardEvent } from "@/lib/insights";
import { relativeTime } from "@/lib/time";

function Stat({ label, value, hint, tone }: { label: string; value: string | number; hint?: string; tone?: "ok" | "bad" }) {
  return (
    <div className="rounded-lg border border-border bg-surface px-4 py-3">
      <div className="text-xs text-secondary">{label}</div>
      <div className={`mt-1 text-2xl font-semibold tabular-nums ${tone === "bad" ? "text-status-bad" : tone === "ok" ? "text-status-ok" : ""}`}>{value}</div>
      {hint && <div className="mt-0.5 text-[13px] text-secondary">{hint}</div>}
    </div>
  );
}

const ICON: Record<string, typeof Activity> = { deployment: Cloud, release: Tag, pull_request: GitPullRequest, ci_run: Workflow };
const TONE: Record<string, "success" | "danger" | "neutral" | "warning"> = { verified: "success", success: "success", failure: "danger", running: "warning", merged: "success", open: "neutral" };
const TAB: Record<string, string> = { deployment: "deployments", release: "releases", ci_run: "ci", pull_request: "activity" };

function EventRow({ e }: { e: DashboardEvent }) {
  const Icon = ICON[e.kind] ?? Activity;
  return (
    <li className="flex items-center gap-3 px-4" style={{ height: 52 }}>
      <Icon className="size-4 shrink-0 text-secondary" strokeWidth={1.75} />
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-2 whitespace-nowrap">
          <Link href={`/projects/${e.project_id}/apps/${e.app_id}/${TAB[e.kind] ?? ""}`} className="min-w-0 truncate text-sm font-medium hover:underline underline-offset-4">{e.title}</Link>
          {e.status && <Badge tone={TONE[e.status] ?? "neutral"} className="h-5 shrink-0 px-2 text-[11px]">{e.status}</Badge>}
        </div>
        <div className="truncate text-xs text-secondary">{e.project} / {e.app}{e.detail && <> · <span className="font-mono">{e.detail}</span></>}</div>
      </div>
      <span className="shrink-0 text-xs text-secondary">{e.at ? relativeTime(e.at) : ""}</span>
    </li>
  );
}

export function DashboardView({ data }: { data: Dashboard }) {
  const deployed = (data.deployments_today.success ?? 0) + (data.deployments_today.verified ?? 0);
  const deployFailed = data.deployments_today.failure ?? 0;
  const ciFailed = data.ci_today.failure ?? 0;
  const ciTotal = Object.values(data.ci_today).reduce((a, b) => a + b, 0);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat label="Apps" value={data.apps} />
        <Stat label="Deployments today" value={deployed} hint={`${data.deployments_today.verified ?? 0} verified`} tone={deployed > 0 ? "ok" : undefined} />
        <Stat label="Deploys failed today" value={deployFailed} tone={deployFailed > 0 ? "bad" : undefined} />
        <Stat label="CI runs today" value={ciTotal} hint={`${ciFailed} failed`} tone={ciFailed > 0 ? "bad" : undefined} />
        <Stat label="Releases this week" value={data.releases_week} />
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <Panel>
          <PanelHeader title="Latest activity" aside={<span className="text-[13px] text-secondary">{data.events.length} events</span>} />
          {data.events.length === 0 ? <EmptyState icon={Activity} title="Nothing yet" text="Releases, deployments, CI runs and pull requests land here as the apps sync." /> : <ul className="divide-y divide-border-subtle">{data.events.map((e, i) => <EventRow key={`${e.kind}-${e.app_id}-${i}`} e={e} />)}</ul>}
        </Panel>
        <Panel>
          <PanelHeader title="Apps without CI" aside={<Badge tone={data.without_ci.length ? "warning" : "success"} className="h-5 px-2 text-[11px]">{data.without_ci.length}</Badge>} />
          {data.without_ci.length === 0 ? (
            <EmptyState icon={ShieldCheck} title="Every app reads a CI" />
          ) : (
            <ul className="divide-y divide-border-subtle">
              {data.without_ci.map((a) => (
                <li key={a.app_id} className="flex items-center gap-3 px-4" style={{ height: 52 }}>
                  <TriangleAlert className="size-4 shrink-0 text-status-warn" strokeWidth={1.75} />
                  <div className="min-w-0 flex-1"><Link href={`/projects/${a.project_id}/apps/${a.app_id}/ci/connect`} className="block truncate text-sm font-medium hover:underline underline-offset-4">{a.app}</Link><div className="truncate text-xs text-secondary">{a.project}</div></div>
                  <Rocket className="size-3.5 shrink-0 text-secondary" strokeWidth={1.75} />
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  );
}
