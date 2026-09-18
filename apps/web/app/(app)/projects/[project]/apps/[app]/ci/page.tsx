import { ciHostsOf, ciOf } from "@/lib/ci";
import { CiPanel } from "@/features/ci";
import { loadApp } from "@/features/projects/load";

export default async function CiPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const [state, hosts] = await Promise.all([ciOf(view.projectId, view.appId), ciHostsOf()]);
  const defaultBranch = view.branches.find((b) => b.name === "main" || b.name === "master")?.name ?? view.branch;
  return (
    <CiPanel
      projectId={view.projectId}
      appId={view.appId}
      state={state}
      hosts={hosts}
      sourceKind={view.sourceKind}
      defaultBranch={defaultBranch}
      canConfigure={!!view.can["app.configure"]}
      canSync={!!view.can["app.sync"]}
    />
  );
}
