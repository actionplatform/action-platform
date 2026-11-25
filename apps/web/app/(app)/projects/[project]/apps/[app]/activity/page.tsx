import { Activity } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel } from "@/components/ui/panel";
import { appPath } from "@/lib/app-routes";
import { ciOf } from "@/lib/ci";
import { appActivityOf, type EventKind, eventKind } from "@/lib/insights";
import { pageQuery } from "@/lib/page";
import { pullRequestsPage } from "@/lib/pull-requests";
import { ActivityFilter, PullRequestsTable } from "@/features/activity";
import { RunsTable } from "@/features/ci";
import { EventRow } from "@/features/insights";
import type { AppView } from "@/features/projects";
import { loadApp } from "@/features/projects/load";

const EMPTY: Record<string, string> = {
  all: "Releases, deployments, CI runs and pull requests of this app land here as it syncs.",
  release: "Releases land here when one is cut or the next sync imports them.",
  deployment: "Deployments land here when a release reaches a scope.",
};

async function Content({ kind, query, view, hasHost }: { kind: EventKind | null; query: Record<string, string | string[] | undefined>; view: AppView; hasHost: boolean }) {
  const { page, per } = pageQuery(query);
  if (kind === "pull_request") {
    const pulls = await pullRequestsPage(view.projectId, view.appId, page, per);
    return <PullRequestsTable page={pulls} currentBranch={view.branch} repositoryUrl={view.repositoryUrl} hasHost={hasHost} />;
  }
  if (kind === "ci_run") {
    const state = await ciOf(view.projectId, view.appId, page, per);
    return <RunsTable projectId={view.projectId} appId={view.appId} state={state} canSync={!!view.can["app.sync"]} connectHref={view.can["app.configure"] ? appPath(view.projectId, view.appId, "settings?tab=ci") : null} />;
  }
  const events = await appActivityOf(view.projectId, view.appId, kind);
  return (
    <Panel>
      {events.length === 0 ? (
        <EmptyState icon={Activity} title="Nothing yet" text={EMPTY[kind ?? "all"]} />
      ) : (
        <ul className="divide-y divide-border-subtle">{events.map((e, i) => <EventRow key={`${e.kind}-${i}`} event={e} scoped />)}</ul>
      )}
    </Panel>
  );
}

export default async function ActivityPage({ params, searchParams }: { params: Promise<{ project: string; app: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { project, app } = await params;
  const query = await searchParams;
  const kind = eventKind(query.kind);
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view, currentHost } = loaded;
  return (
    <div className="space-y-4">
      <ActivityFilter base={appPath(view.projectId, view.appId, "activity")} current={kind} />
      <Content kind={kind} query={query} view={view} hasHost={!!currentHost && !!view.repository} />
    </div>
  );
}
