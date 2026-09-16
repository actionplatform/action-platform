import { Plus } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiOffline } from "@/components/api-offline";
import { PageHeader } from "@/components/layout/page";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Table, Td, Th } from "@/components/ui/table";
import { api, type AppRow } from "@/lib/api";
import { appsOf, projectById } from "@/lib/projects";


import { requireOrg } from "@/lib/session";
import { AddForm } from "@/features/projects";
import { AppCards } from "@/features/projects";
import { LiveList, RemoveButton } from "@/features/projects";
import { v1 } from "@/lib/v1";

export default async function ProjectPage({ params }: { params: Promise<{ project: string }> }) {
  const { project: projectId } = await params;
  const { session, org } = await requireOrg();
  const project = await projectById(org.id, projectId);
  const manage = !!session.grants["project.manage"];
  if (!project) notFound();

  const apps = await appsOf(project.id);
  const tearing = new Set(
    (await Promise.all(apps.map(async (a) => ((await v1.jobs(a.registryId, "destroy").catch(() => [])).some((j) => j.status === "queued" || j.status === "running") ? a.id : null)))).filter((id): id is string => id !== null),
  );

  let rows: Map<string, AppRow>;
  let catalog: { types: { id: string; label: string; description: string }[]; stacks: { id: string; label: string }[] };
  try {
    const [list, matrix] = await Promise.all([api.apps.list(), api.matrix()]);
    rows = new Map(list.map((r) => [r.id, r]));
    catalog = { types: matrix.types.filter((t) => t.id !== "empty"), stacks: matrix.stacks };
  } catch (e) {
    return <ApiOffline error={e} />;
  }

  return (
    <>
      <PageHeader
        title={project.name}
        description={project.description || `Apps in ${project.name}.`}
        actions={manage ? <Link href={`/projects/${project.id}/apps/new`}><Button><Plus className="size-4" /> New app</Button></Link> : undefined}
      />

      {manage && <div className="mb-6"><AddForm projectId={project.id} types={catalog.types} stacks={catalog.stacks} /></div>}
      <LiveList active={tearing.size > 0} />

      <div className="md:hidden">
        <AppCards projectId={project.id} apps={apps.map((a) => ({ id: a.id, name: a.name, registryId: a.registryId, tearing: tearing.has(a.id) }))} rows={rows} manage={manage} />
      </div>

      <Card className="hidden md:block">
        <Table>
          <thead>
            <tr><Th>name</Th><Th>type</Th><Th>language</Th><Th>branch</Th><Th>version</Th><Th>repository</Th><Th /></tr>
          </thead>
          <tbody>
            {apps.length === 0 && (
              <tr><Td colSpan={7} className="text-muted-foreground text-center py-8">No apps yet. Create one from a template or add a repository.</Td></tr>
            )}
            {apps.map((a) => {
              const r = rows.get(a.registryId);
              return (
                <tr key={a.id} className="hover:bg-surface-hover">
                  <Td>
                    <Link href={`/projects/${project.id}/apps/${a.id}`} className="font-medium hover:underline underline-offset-4">{a.name}</Link>
                    {tearing.has(a.id) && <Badge tone="warning" className="ml-2">tearing down</Badge>}
                    {r && !r.exists && <Badge tone="bad" className="ml-2">missing</Badge>}
                    {!r && <Badge className="ml-2">not on API</Badge>}
                  </Td>
                  <Td>{r?.type ?? "—"}</Td>
                  <Td>{r?.language ?? "—"}</Td>
                  <Td><code className="font-mono text-xs">{r?.branch ?? "—"}</code></Td>
                  <Td>{r?.last_version ?? "—"}</Td>
                  <Td className="text-muted-foreground font-mono text-xs">{r?.url || "no remote"}</Td>
                  <Td className="text-right">{manage && !tearing.has(a.id) && <RemoveButton projectId={project.id} appId={a.id} name={a.name} repositoryUrl={r?.url || null} />}</Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      </Card>
    </>
  );
}
