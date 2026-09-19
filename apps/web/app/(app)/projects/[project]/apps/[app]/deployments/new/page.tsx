import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { v1 } from "@/lib/v1";
import { scopesOf } from "@/lib/scopes";
import { DeployCard } from "@/features/deployments";
import { loadApp } from "@/features/projects/load";

export default async function NewDeploymentPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const base = `/projects/${view.projectId}/apps/${view.appId}`;
  const [jobs, scopes] = await Promise.all([v1.jobs(view.registryId, "deploy").catch(() => []), scopesOf(view.projectId, view.appId).catch(() => ({ items: [] }))]);
  return (
    <div className="space-y-4">
      <Link href={`${base}/deployments`} className="inline-flex items-center gap-1.5 text-[13px] text-secondary hover:text-foreground"><ArrowLeft className="size-3.5" strokeWidth={1.75} /> Deployments</Link>
      <DeployCard view={view} scopes={scopes.items} liveStages={jobs.filter((j) => j.status === "queued" || j.status === "running").map((j) => j.stage ?? "dev")} />
    </div>
  );
}
