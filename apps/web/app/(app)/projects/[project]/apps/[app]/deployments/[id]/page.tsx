import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Panel, PanelBody } from "@/components/ui/panel";
import { ApiError, type DeployResult } from "@/lib/api";
import { appPath } from "@/lib/app-routes";
import { type CiDeployRun, type PipelineRunDetail, deployRunsOf, pipelineRunOf } from "@/lib/ci";
import { v1 } from "@/lib/v1";
import { RunView } from "@/features/ci";
import { DeploymentView } from "@/features/deployments";
import { rolloutsOf } from "@/features/deployments/load";
import { loadApp } from "@/features/projects/load";

type Found = { run: CiDeployRun; detail: PipelineRunDetail | null; error: string | null };

async function ciRunsOf(projectId: string, appId: string, job: Awaited<ReturnType<typeof v1.job>>): Promise<{ runs: Found[]; error: string | null }> {
  const rows = Array.isArray(job.result) ? (job.result as DeployResult[]) : [];
  const version = rows[0]?.version || job.version;
  if (job.kind !== "deploy" || job.dry_run || !version) return { runs: [], error: null };
  try {
    const runs = await deployRunsOf(projectId, appId, { stage: job.stage ?? null, version, since: job.started_at ?? job.created_at, until: job.finished_at ?? null, urls: rows.map((r) => r.url).filter((u): u is string => !!u) });
    return {
      runs: await Promise.all(runs.map(async (run) => {
        try {
          return { run, detail: await pipelineRunOf(projectId, appId, run.run.job, run.run.number), error: null };
        } catch (e) {
          return { run, detail: null, error: e instanceof ApiError ? e.message : "The CI did not answer." };
        }
      })),
      error: null,
    };
  } catch (e) {
    return { runs: [], error: e instanceof ApiError ? e.message : "The CI did not answer." };
  }
}

export default async function DeploymentPage({ params }: { params: Promise<{ project: string; app: string; id: string }> }) {
  const { project, app, id } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const job = await v1.job(decodeURIComponent(id)).catch((e) => {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  });
  if (job.app_id !== view.appId || (job.kind !== "deploy" && job.kind !== "destroy")) notFound();
  const base = appPath(view.projectId, view.appId, "");
  const [ci, rollouts] = await Promise.all([ciRunsOf(view.projectId, view.appId, job), rolloutsOf(view.projectId, view.appId, job.id)]);
  return (
    <div className="space-y-4">
      <Link href={appPath(view.projectId, view.appId, "deployments")} className="inline-flex items-center gap-1.5 text-[13px] text-secondary hover:text-foreground"><ArrowLeft className="size-3.5" strokeWidth={1.75} /> Deployments</Link>
      <DeploymentView job={job} base={base} projectId={view.projectId} appId={view.appId} rollouts={rollouts} registryId={view.registryId} canDeploy={!!view.can["app.release"] && !!view.repositoryUrl}>
        {ci.error && <Panel><PanelBody className="text-[13px] text-secondary">CI run: {ci.error}</PanelBody></Panel>}
        {ci.runs.map(({ run, detail, error }) => (
          <section key={`${run.run.job}#${run.run.number}`} aria-label={`CI run of ${run.target}`} className="space-y-2">
            <h2 className="text-sm font-semibold">CI run of {run.target}</h2>
            {detail ? (
              <RunView projectId={view.projectId} appId={view.appId} base={base} repositoryUrl={view.repositoryUrl ?? null} detail={detail} tab={detail.supports.log ? "log" : "details"} embedded />
            ) : (
              <Panel><PanelBody className="text-[13px] text-secondary">{error}</PanelBody></Panel>
            )}
          </section>
        ))}
      </DeploymentView>
    </div>
  );
}
