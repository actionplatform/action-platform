import { PageHeader } from "@/components/layout/page";
import { api, type Matrix } from "@/lib/api";
import { appsOf, projectsOf } from "@/lib/projects";
import { roleOf } from "@/lib/orgs";
import { grantsOf } from "@/lib/permissions";
import { requireOrg } from "@/lib/session";
import { TemplatesCatalog } from "./templates-catalog";
import { TemplatesErrorState } from "./templates-empty-state";

export const dynamic = "force-dynamic";

export default async function TemplatesPage() {
  const { session, org } = await requireOrg();
  const grants = grantsOf(await roleOf(session.user.id, org.id));

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

  return <TemplatesCatalog matrix={matrix} targets={grants["app.configure"] ? targets : []} canCreate={grants["project.manage"]} />;
}
