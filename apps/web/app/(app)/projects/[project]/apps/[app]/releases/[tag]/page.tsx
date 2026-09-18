import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { timelineOf } from "@/lib/insights";
import { TimelineView } from "@/features/insights";
import { loadApp } from "@/features/projects/load";

export default async function ReleaseTimelinePage({ params }: { params: Promise<{ project: string; app: string; tag: string }> }) {
  const { project, app, tag } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const data = await timelineOf(view.projectId, view.appId, decodeURIComponent(tag));
  return (
    <div className="space-y-4">
      <Link href={`/projects/${view.projectId}/apps/${view.appId}/releases`} className="inline-flex items-center gap-1.5 text-[13px] text-secondary hover:text-foreground"><ArrowLeft className="size-3.5" strokeWidth={1.75} /> Releases</Link>
      <TimelineView data={data} repositoryUrl={view.repositoryUrl} />
    </div>
  );
}
