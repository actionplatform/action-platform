import { ciOf } from "@/lib/ci";
import { appPath } from "@/lib/app-routes";
import { protectionOf } from "@/lib/protection";
import { pullRequestsPage } from "@/lib/pull-requests";
import { CurrentBranchCard, OpenedBanner } from "@/features/activity";
import { CommitsCard } from "@/features/projects";
import { HealthCard } from "@/features/projects";
import { loadApp } from "@/features/projects/load";
import { SourceCard } from "@/features/projects";
import { PendingChangesBanner, SummaryGrid } from "@/features/projects";
import { ProtectionSummary } from "@/features/protection";

export default async function OverviewPage({ params, searchParams }: { params: Promise<{ project: string; app: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { project, app } = await params;
  const query = await searchParams;
  const opened = Array.isArray(query.opened) ? query.opened[0] : query.opened;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const base = appPath(view.projectId, view.appId, "");
  const [ci, pulls, protection] = await Promise.all([
    ciOf(view.projectId, view.appId, 1, 100).catch(() => null),
    pullRequestsPage(view.projectId, view.appId, 1, 100).then((p) => p.items).catch(() => []),
    protectionOf(view.projectId, view.appId),
  ]);
  const highlighted = opened ? pulls.find((p) => String(p.number) === opened) : null;

  return (
    <>
      <SummaryGrid view={view} />
      <PendingChangesBanner view={view} base={base} />
      {opened && <div className="mt-4"><OpenedBanner number={Number(opened)} url={highlighted?.url ?? null} branch={highlighted?.head ?? view.branch} base={highlighted?.base ?? "main"} /></div>}
      <div className="mt-4 grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <div className="space-y-4">
          <CurrentBranchCard view={view} ci={ci} pulls={pulls} newHref={appPath(view.projectId, view.appId, "pull-requests/new")} ciSettingsHref={appPath(view.projectId, view.appId, "settings?tab=ci")} />
          <HealthCard view={view} footer={<ProtectionSummary protection={protection} settingsHref={appPath(view.projectId, view.appId, "settings")} />} />
          <CommitsCard commits={view.commits} repositoryUrl={view.repositoryUrl} />
        </div>
        <SourceCard view={view} base={base} />
      </div>
    </>
  );
}
