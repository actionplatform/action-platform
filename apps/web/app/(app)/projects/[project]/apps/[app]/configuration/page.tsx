import { api } from "@/lib/api";
import { requireOrg } from "@/lib/session";
import { sourceSpecsOf } from "@/lib/template-sources";
import { ConfigurationPanels } from "../configuration-panels";
import { loadApp } from "../load";
import { SourceCard } from "../source-card";

export default async function ConfigurationPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const base = `/projects/${view.projectId}/apps/${view.appId}`;
  const { org } = await requireOrg();
  const matrix = await api.matrix(await sourceSpecsOf(org.id));
  const clouds = matrix.clouds.filter((c) => (c.types.length === 0 || c.types.includes(view.type ?? "")) && (c.languages.length === 0 || c.languages.includes(view.language ?? "")));

  return (
    <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
      <ConfigurationPanels view={view} clouds={clouds.map((c) => ({ name: c.name, description: c.description, source: c.source }))} services={matrix.services} />
      <SourceCard view={view} base={base} />
    </div>
  );
}
