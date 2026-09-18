import { ciOf } from "@/lib/ci";
import { RunsTable } from "@/features/ci";
import { loadApp } from "@/features/projects/load";

export default async function CiPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const state = await ciOf(view.projectId, view.appId);
  return <RunsTable projectId={view.projectId} appId={view.appId} state={state} canSync={!!view.can["app.sync"]} connectHref={view.can["app.configure"] ? `/projects/${view.projectId}/apps/${view.appId}/ci/connect` : null} />;
}
