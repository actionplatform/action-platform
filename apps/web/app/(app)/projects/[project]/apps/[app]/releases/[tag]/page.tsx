import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { timelineOf } from "@/lib/insights";
import { readinessOf } from "@/lib/releases";
import { TimelineView } from "@/features/insights";
import { loadApp } from "@/features/projects/load";
import { ReadinessPanel } from "@/features/readiness";

export default async function ReleaseTimelinePage({ params }: { params: Promise<{ project: string; app: string; tag: string }> }) {
  const { project, app, tag } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const decoded = decodeURIComponent(tag);
  const [data, readiness] = await Promise.all([timelineOf(view.projectId, view.appId, decoded), readinessOf(view.projectId, view.appId, decoded).catch(() => [])]);
  return (
    <div className="space-y-4">
      <Link href={`/projects/${view.projectId}/apps/${view.appId}/releases`} className="inline-flex items-center gap-1.5 text-[13px] text-secondary hover:text-foreground"><ArrowLeft className="size-3.5" strokeWidth={1.75} /> Releases</Link>
      <ReadinessPanel projectId={view.projectId} appId={view.appId} tag={decoded} initial={readiness} canCheck={!!view.can["app.release"]} />
      <TimelineView data={data} repositoryUrl={view.repositoryUrl} />
    </div>
  );
}
