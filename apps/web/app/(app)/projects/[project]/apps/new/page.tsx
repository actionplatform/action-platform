import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiOffline } from "@/components/api-offline";
import { PageHeader } from "@/components/layout/page";
import { api, type Matrix } from "@/lib/api";
import { projectById, projectsOf } from "@/lib/projects";
import { requireOrg } from "@/lib/session";
import { hostsOf } from "@/lib/source-hosts";
import { hostAccess } from "@/lib/host-access";
import { appFor } from "@/lib/oauth";
import { sourceSpecsOf } from "@/lib/template-sources";
import { Wizard } from "./wizard";

type Search = { type?: string; stack?: string; template?: string; source?: string };

export default async function NewAppPage({ params, searchParams }: { params: Promise<{ project: string }>; searchParams: Promise<Search> }) {
  const { project: projectId } = await params;
  const query = await searchParams;
  const { org } = await requireOrg();

  const fixed = projectId !== "_";
  const project = fixed ? await projectById(org.id, projectId) : null;
  if (fixed && !project) notFound();
  const [projects, hosts] = await Promise.all([projectsOf(org.id), hostsOf(org.id)]);
  const slug = appFor("github")?.slug ?? null;
  const owners = Object.fromEntries(
    await Promise.all(
      hosts.map(async (h) => {
        if (h.kind === "generic") return [h.id, { accounts: [] as string[], installUrl: null as string | null }] as const;
        const access = await hostAccess(org.id, h.id, slug);
        if (!access.ok) return [h.id, { accounts: [], installUrl: null }] as const;
        return [h.id, { accounts: [...new Set([...access.installations.filter((i) => i.canCreateRepos).map((i) => i.account)])], installUrl: access.installUrl }] as const;
      }),
    ),
  );

  let matrix: Matrix;
  try {
    matrix = await api.matrix(await sourceSpecsOf(org.id));
  } catch (e) {
    return <ApiOffline error={e} />;
  }

  const preset = query.template && query.type ? { type: query.type, stack: query.stack ?? null, template: query.template, source: query.source ?? "official" } : null;

  return (
    <>
      <div className="mb-4 text-xs text-secondary">
        <Link href="/projects" className="hover:text-foreground">Projects</Link>
        {project && <> / <Link href={`/projects/${project.id}`} className="hover:text-foreground">{project.name}</Link></>}
        {" / "}<span className="text-foreground">New app</span>
      </div>
      <PageHeader title="Create project" description="Choose a foundation and configure your new project." />
      <Wizard matrix={matrix} preset={preset} projectId={project?.id ?? null} projects={projects.map((p) => ({ id: p.id, name: p.name }))} hosts={hosts.map((h) => ({ id: h.id, name: h.name, kind: h.kind, defaultOwner: h.defaultOwner, owners: owners[h.id].accounts, installUrl: owners[h.id].installUrl }))} />
    </>
  );
}
