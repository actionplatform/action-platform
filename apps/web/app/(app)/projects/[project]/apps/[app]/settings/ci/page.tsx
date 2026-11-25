import { ciHostsOf, ciOf } from "@/lib/ci";
import { appPath } from "@/lib/app-routes";
import { ConnectCi } from "@/features/ci";
import { loadApp } from "@/features/projects/load";

export default async function AppCiSettingsPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const [state, hosts] = await Promise.all([ciOf(view.projectId, view.appId), ciHostsOf()]);
  return <ConnectCi projectId={view.projectId} appId={view.appId} state={state} hosts={hosts} sourceKind={view.sourceKind} backHref={appPath(view.projectId, view.appId, "activity?kind=ci_run")} canEdit={!!view.can["app.configure"]} />;
}
