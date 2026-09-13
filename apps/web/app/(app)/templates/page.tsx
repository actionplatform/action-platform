import { PageHeader } from "@/components/layout/page";
import { api, type Matrix } from "@/lib/api";
import { appsOf, projectsOf } from "@/lib/projects";
import { roleOf } from "@/lib/orgs";
import { grantsOf } from "@/lib/permissions";
import { requireOrg } from "@/lib/session";
import { sourceSpecsOf, templateSourcesOf } from "@/lib/template-sources";
import { type SourceRow, TemplateSources } from "./template-sources";
import { TemplatesCatalog } from "./templates-catalog";
import { TemplatesErrorState } from "./templates-empty-state";

export const dynamic = "force-dynamic";

export default async function TemplatesPage() {
  const { session, org } = await requireOrg();
  const grants = grantsOf(await roleOf(session.user.id, org.id));

  const [rows, specs] = await Promise.all([templateSourcesOf(org.id), sourceSpecsOf(org.id)]);
  let matrix: Matrix | null = null;
  try {
    matrix = await api.matrix(specs);
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
