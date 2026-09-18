import { loadApp } from "@/features/projects/load";
import { ReleasesTable } from "@/features/releases";

export default async function ReleasesPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view, releases, stored } = loaded;
  const canRelease = !!view.can["app.release"] && !!view.repositoryUrl;
  return <ReleasesTable stored={stored} fromGit={releases} repositoryUrl={view.repositoryUrl} newHref={canRelease ? `/projects/${view.projectId}/apps/${view.appId}/releases/new` : null} />;
}
