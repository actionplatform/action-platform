import { GitPullRequestArrow, Plus, Settings } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiOffline } from "@/components/api-offline";
import { PageHeader } from "@/components/layout/page";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Cell } from "@/components/ui/data-table";
import { TBody, Table, Td, Th, Tr } from "@/components/ui/table";
import { api, type AppRow } from "@/lib/api";
import { appsOf, projectById } from "@/lib/projects";


import { requireOrg } from "@/lib/session";
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

      <div className="md:hidden">
        <AppCards projectId={project.id} apps={apps.map((a) => ({ id: a.id, name: a.name, registryId: a.registryId, tearing: tearing.has(a.id) }))} rows={rows} manage={manage} />
      </div>

      <Card className="hidden md:block">
        <Table columns={[{ width: 24 }, { width: 9, hideBelow: "lg" }, { width: 11, hideBelow: "lg" }, { width: 14 }, { width: 12 }, { width: 24, hideBelow: "lg" }, ...(manage ? [{ width: "56px" }] : [])]}>
          <thead>
            <tr><Th>Name</Th><Th hideBelow="lg">Type</Th><Th hideBelow="lg">Language</Th><Th>Branch</Th><Th>Version</Th><Th hideBelow="lg">Repository</Th>{manage && <Th><span className="sr-only">Actions</span></Th>}</tr>
          </thead>
          <TBody>
            {apps.length === 0 && (
              <tr><Td colSpan={manage ? 7 : 6} className="py-8 text-center text-secondary">No apps yet. Create one with New app, from a template or an existing repository.</Td></tr>
            )}
            {apps.map((a) => {
              const r = rows.get(a.registryId);
              return (
                <Tr key={a.id}>
                  <Td>
                    <Cell title={[a.name, tearing.has(a.id) && "tearing down", r && !r.exists && "missing", !r && "not on API"].filter(Boolean).join(" · ")}>
                      <span className="inline-flex items-center gap-2 align-middle">
                        <Link href={`/projects/${project.id}/apps/${a.id}`} className="font-medium hover:underline underline-offset-4">{a.name}</Link>
                        {tearing.has(a.id) && <Badge tone="warning">tearing down</Badge>}
                        {r && !r.exists && <Badge tone="bad">missing</Badge>}
                        {!r && <Badge>not on API</Badge>}
                      </span>
                    </Cell>
                  </Td>
                  <Td hideBelow="lg"><Cell muted>{r?.type ?? "—"}</Cell></Td>
                  <Td hideBelow="lg"><Cell muted>{r?.language ?? "—"}</Cell></Td>
                  <Td><Cell mono muted>{r?.branch ?? "—"}</Cell></Td>
                  <Td><Cell mono>{r?.last_version ?? "—"}</Cell></Td>
                  <Td hideBelow="lg"><Cell mono muted>{r?.url || "no remote"}</Cell></Td>
                  {manage && <Td align="right" className="py-1">{!tearing.has(a.id) && <RemoveButton projectId={project.id} appId={a.id} name={a.name} repositoryUrl={r?.url || null} />}</Td>}
                </Tr>
              );
            })}
          </TBody>
        </Table>
      </Card>
    </>
  );
}
