import { notFound } from "next/navigation";
import { ApiOffline } from "@/components/api-offline";
import { PageHeader } from "@/components/layout/page";
import { api } from "@/lib/api";
import { projectById } from "@/lib/projects";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";
import { AdoptionView } from "@/features/projects";

export default async function AdoptionPage({ params }: { params: Promise<{ project: string }> }) {
  const { project: projectId } = await params;
  const { session, org } = await requireOrg();
  const project = await projectById(org.id, projectId);
  if (!project) notFound();

  let rows: Awaited<ReturnType<typeof v1.adoption>>;
  let types: { id: string; label: string }[];
  try {
    const [adoption, matrix] = await Promise.all([v1.adoption(project.id), api.matrix()]);
    rows = adoption;
    types = matrix.types.filter((t) => t.id !== "empty").map((t) => ({ id: t.id, label: t.label }));
  } catch (e) {
    return <ApiOffline error={e} />;
  }

  return (
    <>
      <PageHeader title={`Adoption · ${project.name}`} description="Bring this project's repositories onto the platform: preview each install plan, then open one pull request per repository." />
      <AdoptionView projectId={project.id} rows={rows} canManage={!!session.grants["project.manage"]} options={{ types }} />
    </>
  );
}
