import { GitRefsCard } from "../git-refs-card";
import { loadApp } from "../load";
import { ReleaseCard } from "../release-card";
import { ReleasesTable } from "../releases-table";

export default async function ReleasesPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view, releases, stored } = loaded;
  const defaultBranch = view.branches.find((b) => view.stableBranches.includes(b.name))?.name ?? null;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,68fr)_minmax(300px,32fr)]">
        <ReleaseCard view={view} />
        <GitRefsCard branches={view.branches} repository={view.repository} repositoryUrl={view.repositoryUrl} sourceKind={view.sourceKind} defaultBranch={defaultBranch} />
      </div>
      <ReleasesTable stored={stored} fromGit={releases} repositoryUrl={view.repositoryUrl} />
    </div>
  );
}
