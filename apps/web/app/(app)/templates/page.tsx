import { type Grants } from "@/lib/permissions";
import { PageHeader } from "@/components/layout/page";
import { api, type Matrix } from "@/lib/api";
import { appsOf, projectsOf } from "@/lib/projects";

import { requireOrg } from "@/lib/session";
import { templateSourcesOf } from "@/lib/template-sources";
import { type SourceRow, TemplateSources } from "@/features/templates";
import { TemplatesCatalog } from "@/features/templates";
import { TemplatesErrorState } from "@/features/templates";

export const dynamic = "force-dynamic";

export default async function TemplatesPage() {
  const { session, org } = await requireOrg();
  const grants = session.grants as Grants;

  const rows = await templateSourcesOf(org.id);
  let matrix: Matrix | null = null;
  try {
    matrix = await api.matrix();
  } catch {}

  if (!matrix) {
    return (
      <>
        <PageHeader title="Templates" description="Start faster with production-ready foundations for apps, libraries, documentation, plugins, and cloud services." />
        <TemplatesErrorState />
      </>
    );
  }

  const projects = await projectsOf(org.id);
  const targets = (await Promise.all(projects.map(async (p) => (await appsOf(p.id)).map((a) => ({ id: a.id, projectId: p.id, registryId: a.registryId, name: a.name, project: p.name }))))).flat();

  const ids = new Map(rows.map((r) => [r.name, r.id]));
  const sources: SourceRow[] = matrix.sources.map((s) => ({ id: ids.get(s.name) ?? null, name: s.name, url: s.url, ref: s.ref, ok: s.ok, error: s.error ?? null, projects: s.projects, clouds: s.clouds, services: s.services, official: s.name === "official" }));

  return <TemplatesCatalog matrix={matrix} targets={grants["app.configure"] ? targets : []} canCreate={grants["project.manage"]} sources={<TemplateSources sources={sources} canManage={grants["org.manage"]} />} />;
}
