import { pullRequestsOf } from "@/lib/pull-requests";
import { OpenedBanner, PullRequestsTable } from "@/features/activity";
import { loadApp } from "@/features/projects/load";

export default async function ActivityPage({ params, searchParams }: { params: Promise<{ project: string; app: string }>; searchParams: Promise<{ opened?: string }> }) {
  const { project, app } = await params;
  const { opened } = await searchParams;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view, currentHost } = loaded;
  const pulls = await pullRequestsOf(view.projectId, view.appId);
  const highlighted = opened ? pulls.find((p) => String(p.number) === opened) : null;
  const canFlow = !!view.can["app.flow"] && !!view.repositoryUrl;
  return (
    <div className="space-y-4">
      {opened && <OpenedBanner number={Number(opened)} url={highlighted?.url ?? null} branch={highlighted?.head ?? view.branch} base={highlighted?.base ?? "main"} />}
      <PullRequestsTable rows={pulls} currentBranch={view.branch} repositoryUrl={view.repositoryUrl} hasHost={!!currentHost && !!view.repository} newHref={canFlow ? `/projects/${view.projectId}/apps/${view.appId}/activity/new` : null} />
    </div>
  );
}
