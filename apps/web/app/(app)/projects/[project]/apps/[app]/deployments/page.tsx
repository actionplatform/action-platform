import { v1 } from "@/lib/v1";
import { DeploymentsTable } from "@/features/deployments";
import { TargetsPanel } from "@/features/deployments";
import { deploymentsOf } from "@/lib/deployments";
import { loadApp } from "@/features/projects/load";

export default async function DeploymentsPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const base = `/projects/${view.projectId}/apps/${view.appId}`;
  const [deploys, teardowns, records] = await Promise.all([
    v1.jobs(view.registryId, "deploy", 200).catch(() => []),
    v1.jobs(view.registryId, "destroy", 200).catch(() => []),
    deploymentsOf(view.projectId, view.appId).catch(() => ({ targets: [], deployments: [], error: null })),
  ]);
  const jobs = [...deploys, ...teardowns].sort((a, b) => (b.created_at > a.created_at ? 1 : b.created_at < a.created_at ? -1 : 0));
  const canDeploy = !!view.can["app.release"] && !!view.repositoryUrl;
  return (
    <div className="space-y-4">
      <TargetsPanel projectId={view.projectId} appId={view.appId} state={records} canSync={!!view.can["app.sync"]} canRecord={!!view.can["app.release"]} />
      <DeploymentsTable jobs={jobs} registryId={view.registryId} canDeploy={canDeploy} newHref={`${base}/deployments/new`} />
    </div>
  );
}
