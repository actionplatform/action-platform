import { ApiError } from "@/lib/api";
import { appPath } from "@/lib/app-routes";
import { pipelinesOf } from "@/lib/ci";
import { PipelinesTable } from "@/features/ci";
import { loadApp } from "@/features/projects/load";

function one(v: string | string[] | undefined): string | null {
  const value = Array.isArray(v) ? v[0] : v;
  return value === undefined ? null : value;
}

export default async function PipelinesPage({ params, searchParams }: { params: Promise<{ project: string; app: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { project, app } = await params;
  const query = await searchParams;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const job = one(query.job);
  const status = one(query.status) || null;
  const data = await pipelinesOf(view.projectId, view.appId, job, status).catch((e) => {
    if (!(e instanceof ApiError) || e.status >= 500 && e.status !== 502) throw e;
    return { kind: "unknown", jobs: [], runs: [], errors: [{ job: job ?? "", error: e.message }] };
  });
  return <PipelinesTable base={appPath(view.projectId, view.appId, "")} data={data} job={job ?? ""} status={status ?? ""} connectHref={view.can["app.configure"] ? appPath(view.projectId, view.appId, "settings?tab=ci") : null} />;
}
