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
  const owners: Record<string, { accounts: { account: string; ok: boolean; why: string | null }[]; installUrl: string | null; problem: string | null }> = Object.fromEntries(
    await Promise.all(
      hosts.map(async (h) => {
        if (h.kind === "generic") return [h.id, { accounts: [] as { account: string; ok: boolean; why: string | null }[], installUrl: null as string | null, problem: null as string | null }] as const;
        const access = await hostAccess(org.id, h.id, slug);
        if (!access.ok) return [h.id, { accounts: [], installUrl: null, problem: access.error }] as const;
        const seen = new Set<string>();
        const accounts = access.installations
          .filter((i) => (seen.has(i.account) ? false : seen.add(i.account)))
          .map((i) => ({ account: i.account, ok: i.canCreateRepos && i.repositories === "all", why: i.canCreateRepos ? (i.repositories === "all" ? null : "installed on selected repositories only") : `app lacks admin:${i.administration} contents:${i.contents}` }));
        return [h.id, { accounts, installUrl: access.installUrl, problem: access.problems[0] ?? null }] as const;
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
      <Wizard matrix={matrix} preset={preset} projectId={project?.id ?? null} projects={projects.map((p) => ({ id: p.id, name: p.name }))} hosts={hosts.map((h) => ({ id: h.id, name: h.name, kind: h.kind, defaultOwner: h.defaultOwner, owners: [...owners[h.id].accounts], installUrl: owners[h.id].installUrl, problem: owners[h.id].problem }))} />
    </>
  );
}
