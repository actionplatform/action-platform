import { GitPullRequestArrow, Plus, Settings } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiOffline } from "@/components/api-offline";
import { PageHeader } from "@/components/layout/page";
import { Button } from "@/components/ui/button";
import { api, type AppRow } from "@/lib/api";
import { appsOf, projectById } from "@/lib/projects";


import { pageQuery, paginate } from "@/lib/page";
import { requireOrg } from "@/lib/session";
import { AppsTable, LiveList } from "@/features/projects";
import { v1 } from "@/lib/v1";

export default async function ProjectPage({ params, searchParams }: { params: Promise<{ project: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { project: projectId } = await params;
  const query = pageQuery(await searchParams, "apps");
  const { session, org } = await requireOrg();
  const project = await projectById(org.id, projectId);
  const manage = !!session.grants["project.manage"];
  if (!project) notFound();

  const apps = await appsOf(project.id);
  const tearing = new Set(
    (await Promise.all(apps.map(async (a) => ((await v1.jobs(a.registryId, "destroy").catch(() => [])).some((j) => j.status === "queued" || j.status === "running") ? a.id : null)))).filter((id): id is string => id !== null),
  );

  let rows: Map<string, AppRow>;
  try {
    rows = new Map((await api.apps.list()).map((r) => [r.id, r]));
  } catch (e) {
    return <ApiOffline error={e} />;
  }

  return (
    <>
      <PageHeader
        title={project.name}
        description={project.description || `Apps in ${project.name}.`}
        actions={<><Link href={`/projects/${project.id}/adoption`}><Button variant="outline"><GitPullRequestArrow className="size-4" /> Adoption</Button></Link>{manage && <Link href={`/projects/${project.id}/settings`}><Button variant="outline"><Settings className="size-4" /> Settings</Button></Link>}{manage && <Link href={`/projects/${project.id}/apps/new`}><Button><Plus className="size-4" /> New app</Button></Link>}</>}
      />

      <LiveList active={tearing.size > 0} />

      <AppsTable
        projectId={project.id}
        apps={paginate(apps, query).items.map((a) => ({ id: a.id, name: a.name, registryId: a.registryId, tearing: tearing.has(a.id) }))}
        paging={{ total: apps.length, page: query.page, per: query.per }}
        rows={Object.fromEntries(rows)}
        manage={manage}
      />
    </>
  );
}
