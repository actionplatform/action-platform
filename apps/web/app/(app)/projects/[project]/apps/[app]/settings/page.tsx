import { api } from "@/lib/api";
import { ciHostsOf, ciOf } from "@/lib/ci";
import { requireOrg } from "@/lib/session";
import { PageTabs, pickTab } from "@/components/layout/page-tabs";
import { ConnectCi } from "@/features/ci";
import { ConfigurationPanels } from "@/features/configuration";
import { DangerZone, RepositoryPanel } from "@/features/projects";
import { loadApp } from "@/features/projects/load";

const TABS = [{ id: "general", label: "General" }, { id: "ci", label: "CI" }];

export default async function SettingsPage({ params, searchParams }: { params: Promise<{ project: string; app: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { project, app } = await params;
  const tab = pickTab(TABS, (await searchParams).tab);
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;

  if (tab === "ci") {
    const [state, hosts] = await Promise.all([ciOf(view.projectId, view.appId), ciHostsOf()]);
    return (
      <>
        <PageTabs label="App settings" tabs={TABS} active={tab} />
        <ConnectCi projectId={view.projectId} appId={view.appId} state={state} hosts={hosts} sourceKind={view.sourceKind} backHref={`/projects/${view.projectId}/apps/${view.appId}/ci`} canEdit={!!view.can["app.configure"]} />
      </>
    );
  }

  await requireOrg();
  const matrix = await api.matrix();
  const clouds = matrix.clouds.filter((c) => (c.types.length === 0 || c.types.includes(view.type ?? "")) && (c.languages.length === 0 || c.languages.includes(view.language ?? "")));

  return (
    <>
      <PageTabs label="App settings" tabs={TABS} active={tab} />
      <div className="space-y-4">
        <RepositoryPanel view={view} hosts={loaded.hosts} currentHost={loaded.currentHost} />
        <ConfigurationPanels view={view} clouds={clouds.map((c) => ({ name: c.name, description: c.description, source: c.source }))} />
        <DangerZone view={view} />
      </div>
    </>
  );
}
