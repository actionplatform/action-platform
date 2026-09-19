import { scopesOf } from "@/lib/scopes";
import { loadApp } from "@/features/projects/load";
import { ScopesTable } from "@/features/scopes";

export default async function ScopesPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const base = `/projects/${view.projectId}/apps/${view.appId}`;
  const scopes = await scopesOf(view.projectId, view.appId).catch(() => ({ items: [], kinds: [], criticalities: [] }));
  return <ScopesTable scopes={scopes.items} projectId={view.projectId} appId={view.appId} canEdit={!!view.can["app.configure"]} newHref={`${base}/scopes/new`} />;
}
