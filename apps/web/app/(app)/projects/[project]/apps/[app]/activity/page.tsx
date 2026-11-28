import { Activity } from "lucide-react";
import Link from "next/link";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel } from "@/components/ui/panel";
import { appPath } from "@/lib/app-routes";
import { appActivityOf, type EventKind, eventKind } from "@/lib/insights";
import { ActivityFilter } from "@/features/activity";
import { EventRow } from "@/features/insights";
import type { AppView } from "@/features/projects";
import { loadApp } from "@/features/projects/load";

const EMPTY: Record<string, string> = {
  all: "Releases, deployments and branch protection changes of this app land here as it syncs.",
  release: "Releases land here when one is cut or the next sync imports them.",
  deployment: "Deployments land here when a release reaches a scope.",
};

async function Content({ kind, view }: { kind: EventKind | null; view: AppView }) {
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
  const { view } = loaded;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <ActivityFilter base={appPath(view.projectId, view.appId, "activity")} current={kind} />
        <Link href={appPath(view.projectId, view.appId, "pipelines")} className="text-[13px] text-secondary hover:text-foreground">CI runs in Pipelines</Link>
      </div>
      <Content kind={kind} view={view} />
    </div>
  );
}
