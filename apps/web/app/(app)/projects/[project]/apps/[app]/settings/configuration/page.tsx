import { api } from "@/lib/api";
import { requireOrg } from "@/lib/session";
import { ConfigurationPanels } from "@/features/configuration";
import { loadApp } from "@/features/projects/load";
import { SourceCard } from "@/features/projects";

export default async function ConfigurationPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const base = `/projects/${view.projectId}/apps/${view.appId}`;
  await requireOrg();
  const matrix = await api.matrix();
  const clouds = matrix.clouds.filter((c) => (c.types.length === 0 || c.types.includes(view.type ?? "")) && (c.languages.length === 0 || c.languages.includes(view.language ?? "")));

  return (
    <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
      <ConfigurationPanels view={view} clouds={clouds.map((c) => ({ name: c.name, description: c.description, source: c.source }))} />
      <SourceCard view={view} base={base} />
    </div>
  );
}
