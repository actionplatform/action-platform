import { pullRequestsOf } from "@/lib/pull-requests";
import { FlowPanel } from "../flow-panel";
import { loadApp } from "../load";
import { PullRequestsCard } from "../pull-requests-card";
import { OpenedBanner } from "./opened-banner";

export default async function ActivityPage({ params, searchParams }: { params: Promise<{ project: string; app: string }>; searchParams: Promise<{ opened?: string }> }) {
  const { project, app } = await params;
  const { opened } = await searchParams;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view, currentHost } = loaded;
  const pulls = await pullRequestsOf(view.appId);
  const highlighted = opened ? pulls.find((p) => String(p.number) === opened) : null;
  return (
    <div className="space-y-4">
      {opened && <OpenedBanner number={Number(opened)} url={highlighted?.url ?? null} branch={highlighted?.head ?? view.branch} base={highlighted?.base ?? "main"} />}
      <FlowPanel view={view} />
      <PullRequestsCard rows={pulls} hasHost={!!currentHost && !!view.repository} currentBranch={view.branch} branches={view.branches.map((b) => b.name)} repositoryUrl={view.repositoryUrl} />
    </div>
  );
}
