import { v1 } from "@/lib/v1";
import { DeployCard } from "@/features/deployments";
import { DeploymentsTable } from "@/features/deployments";
import { loadApp } from "@/features/projects/load";
import { TargetCard } from "@/features/deployments";
import { TargetsPanel } from "@/features/deployments";
import { deploymentsOf } from "@/lib/deployments";

export default async function DeploymentsPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const base = `/projects/${view.projectId}/apps/${view.appId}`;
  const [deploys, teardowns, records] = await Promise.all([
    v1.jobs(view.registryId, "deploy").catch(() => []),
    v1.jobs(view.registryId, "destroy").catch(() => []),
    deploymentsOf(view.projectId, view.appId).catch(() => ({ targets: [], deployments: [], error: null })),
  ]);
  const jobs = [...deploys, ...teardowns].sort((a, b) => (b.created_at > a.created_at ? 1 : b.created_at < a.created_at ? -1 : 0));
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,65fr)_minmax(300px,35fr)]">
        <DeployCard view={view} liveStages={jobs.filter((j) => j.kind === "deploy" && (j.status === "queued" || j.status === "running")).map((j) => j.stage ?? "dev")} />
        <div className="relative">
          <div className="lg:absolute lg:inset-0"><TargetCard view={view} base={base} /></div>
        </div>
      </div>
      <TargetsPanel projectId={view.projectId} appId={view.appId} state={records} canSync={!!view.can["app.sync"]} canRecord={!!view.can["app.release"]} />
      <DeploymentsTable jobs={jobs} registryId={view.registryId} canDeploy={!!view.can["app.release"] && !!view.repositoryUrl} />
    </div>
  );
}
