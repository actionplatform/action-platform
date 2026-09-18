import { ciOf } from "@/lib/ci";
import { pageQuery } from "@/lib/page";
import { RunsTable } from "@/features/ci";
import { loadApp } from "@/features/projects/load";

export default async function CiPage({ params, searchParams }: { params: Promise<{ project: string; app: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { project, app } = await params;
  const { page, per } = pageQuery(await searchParams);
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const state = await ciOf(view.projectId, view.appId, page, per);
  return <RunsTable projectId={view.projectId} appId={view.appId} state={state} canSync={!!view.can["app.sync"]} connectHref={view.can["app.configure"] ? `/projects/${view.projectId}/apps/${view.appId}/ci/connect` : null} canRun={!!view.can["app.flow"]} defaultRef={view.branch} />;
}
