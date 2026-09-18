import { pullRequestsPage } from "@/lib/pull-requests";
import { pageQuery } from "@/lib/page";
import { OpenedBanner, PullRequestsTable } from "@/features/activity";
import { loadApp } from "@/features/projects/load";

export default async function ActivityPage({ params, searchParams }: { params: Promise<{ project: string; app: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { project, app } = await params;
  const query = await searchParams;
  const opened = Array.isArray(query.opened) ? query.opened[0] : query.opened;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view, currentHost } = loaded;
  const { page, per } = pageQuery(query);
  const pulls = await pullRequestsPage(view.projectId, view.appId, page, per);
  const highlighted = opened ? pulls.items.find((p) => String(p.number) === opened) : null;
  const canFlow = !!view.can["app.flow"] && !!view.repositoryUrl;
  return (
    <div className="space-y-4">
      {opened && <OpenedBanner number={Number(opened)} url={highlighted?.url ?? null} branch={highlighted?.head ?? view.branch} base={highlighted?.base ?? "main"} />}
      <PullRequestsTable page={pulls} currentBranch={view.branch} repositoryUrl={view.repositoryUrl} hasHost={!!currentHost && !!view.repository} newHref={canFlow ? `/projects/${view.projectId}/apps/${view.appId}/activity/new` : null} />
    </div>
  );
}
