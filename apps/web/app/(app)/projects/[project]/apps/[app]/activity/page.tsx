import { pullRequestsOf } from "@/lib/pull-requests";
import { FlowPanel } from "../flow-panel";
import { loadApp } from "../load";
import { PullRequestsCard } from "../pull-requests-card";

export default async function ActivityPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view, currentHost } = loaded;
  const pulls = await pullRequestsOf(view.appId);
  return (
    <div className="space-y-4">
      <FlowPanel view={view} />
      <PullRequestsCard rows={pulls} hasHost={!!currentHost && !!view.repository} currentBranch={view.branch} branches={view.branches.map((b) => b.name)} repositoryUrl={view.repositoryUrl} />
    </div>
  );
}
