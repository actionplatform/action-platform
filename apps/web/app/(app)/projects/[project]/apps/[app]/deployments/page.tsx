import { v1 } from "@/lib/v1";
import { DeployCard } from "@/features/deployments";
import { DeploymentsTable } from "@/features/deployments";
import { loadApp } from "@/features/projects/load";
import { TargetCard } from "@/features/deployments";

export default async function DeploymentsPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const base = `/projects/${view.projectId}/apps/${view.appId}`;
  const jobs = await v1.jobs(view.registryId, "deploy").catch(() => []);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,65fr)_minmax(300px,35fr)]">
        <DeployCard view={view} />
        <div className="relative">
          <div className="lg:absolute lg:inset-0"><TargetCard view={view} base={base} /></div>
        </div>
      </div>
      <DeploymentsTable jobs={jobs} registryId={view.registryId} canDeploy={!!view.can["app.release"] && !!view.repositoryUrl} />
    </div>
  );
}
