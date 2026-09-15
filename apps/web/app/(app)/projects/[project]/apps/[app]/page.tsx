import { CommitsCard } from "./commits-card";
import { HealthCard } from "./health-card";
import { loadApp } from "./load";
import { SourceCard } from "./source-card";
import { PendingChangesBanner, SummaryGrid } from "./summary-grid";

export default async function OverviewPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const base = `/projects/${view.projectId}/apps/${view.appId}`;

  return (
    <>
      <SummaryGrid view={view} />
      <PendingChangesBanner view={view} base={base} />
      <div className="mt-4 grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <div className="space-y-4">
          <HealthCard view={view} />
          <CommitsCard commits={view.commits} repositoryUrl={view.repositoryUrl} base={base} />
        </div>
        <SourceCard view={view} base={base} />
      </div>
    </>
  );
}
