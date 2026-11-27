import { notFound } from "next/navigation";
import { ApiError } from "@/lib/api";
import { appPath } from "@/lib/app-routes";
import { pipelineRunOf } from "@/lib/ci";
import { RunView, type RunTab } from "@/features/ci";
import { loadApp } from "@/features/projects/load";

const TABS: RunTab[] = ["log", "tests", "artifacts", "details"];

export default async function PipelineRunPage({ params, searchParams }: { params: Promise<{ project: string; app: string; number: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { project, app, number: raw } = await params;
  const query = await searchParams;
  const number = Number(raw);
  if (!Number.isSafeInteger(number) || number < 0) notFound();
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const job = (Array.isArray(query.job) ? query.job[0] : query.job) ?? "";
  const detail = await pipelineRunOf(view.projectId, view.appId, job, number).catch((e) => {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  });
  const wanted = (Array.isArray(query.tab) ? query.tab[0] : query.tab) as RunTab | undefined;
  const shown = TABS.filter((t) => t === "details" || detail.supports[t]);
  const tab = wanted && shown.includes(wanted) ? wanted : shown[0];
  return <RunView projectId={view.projectId} appId={view.appId} base={appPath(view.projectId, view.appId, "")} repositoryUrl={view.repositoryUrl ?? null} detail={detail} tab={tab} />;
}
