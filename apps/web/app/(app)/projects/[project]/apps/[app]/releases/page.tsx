import { pageQuery } from "@/lib/page";
import { releasesPage } from "@/lib/releases";
import { loadApp } from "@/features/projects/load";
import { ReleasesTable } from "@/features/releases";

export default async function ReleasesPage({ params, searchParams }: { params: Promise<{ project: string; app: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { project, app } = await params;
  const { page, per } = pageQuery(await searchParams);
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const releases = await releasesPage(view.projectId, view.appId, page, per);
  const canRelease = !!view.can["app.release"] && !!view.repositoryUrl;
  return <ReleasesTable page={releases} repositoryUrl={view.repositoryUrl} base={`/projects/${view.projectId}/apps/${view.appId}`} newHref={canRelease ? `/projects/${view.projectId}/apps/${view.appId}/releases/new` : null} />;
}
