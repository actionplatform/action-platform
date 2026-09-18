import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { v1 } from "@/lib/v1";
import { DeployCard } from "@/features/deployments";
import { TargetCard } from "@/features/deployments";
import { loadApp } from "@/features/projects/load";

export default async function NewDeploymentPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const base = `/projects/${view.projectId}/apps/${view.appId}`;
  const jobs = await v1.jobs(view.registryId, "deploy").catch(() => []);
  return (
    <div className="space-y-4">
      <Link href={`${base}/deployments`} className="inline-flex items-center gap-1.5 text-[13px] text-secondary hover:text-foreground"><ArrowLeft className="size-3.5" strokeWidth={1.75} /> Deployments</Link>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,65fr)_minmax(300px,35fr)]">
        <DeployCard view={view} liveStages={jobs.filter((j) => j.status === "queued" || j.status === "running").map((j) => j.stage ?? "dev")} />
        <div className="relative">
          <div className="lg:absolute lg:inset-0"><TargetCard view={view} base={base} /></div>
        </div>
      </div>
    </div>
  );
}
