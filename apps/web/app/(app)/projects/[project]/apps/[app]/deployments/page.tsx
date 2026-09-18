import { v1 } from "@/lib/v1";
import { pageQuery } from "@/lib/page";
import { DeploymentsTable } from "@/features/deployments";
import { loadApp } from "@/features/projects/load";

export default async function DeploymentsPage({ params, searchParams }: { params: Promise<{ project: string; app: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { project, app } = await params;
  const { page, per } = pageQuery(await searchParams);
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const base = `/projects/${view.projectId}/apps/${view.appId}`;
  const jobs = await v1.jobsPage(view.registryId, "deploy,destroy", page, per).catch(() => ({ items: [], total: 0, page, per }));
  const canDeploy = !!view.can["app.release"] && !!view.repositoryUrl;
  return <DeploymentsTable page={jobs} registryId={view.registryId} canDeploy={canDeploy} newHref={`${base}/deployments/new`} />;
}
