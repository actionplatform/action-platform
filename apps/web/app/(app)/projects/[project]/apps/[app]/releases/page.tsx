import { loadApp } from "@/features/projects/load";
import { ReleaseCard } from "@/features/releases";
import { ReleasesTable } from "@/features/releases";

export default async function ReleasesPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view, releases, stored } = loaded;
  return (
    <div className="space-y-4">
      <ReleaseCard view={view} />
      <ReleasesTable stored={stored} fromGit={releases} repositoryUrl={view.repositoryUrl} />
    </div>
  );
}
