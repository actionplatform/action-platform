import { loadApp } from "../load";
import { RefsCard } from "../refs-card";
import { ReleaseCard } from "../release-card";
import { ReleasesTable } from "../releases-table";

export default async function ReleasesPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view, releases, stored } = loaded;
  const base = `/projects/${view.projectId}/apps/${view.appId}`;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <ReleaseCard view={view} />
        <div className="relative">
          <div className="lg:absolute lg:inset-0"><RefsCard branches={view.branches} tags={view.tags} repositoryUrl={view.repositoryUrl} base={base} fill showTags={false} /></div>
        </div>
      </div>
      <ReleasesTable stored={stored} fromGit={releases} repositoryUrl={view.repositoryUrl} />
    </div>
  );
}
