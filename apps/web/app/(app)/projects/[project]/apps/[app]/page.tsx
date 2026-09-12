import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiOffline } from "@/components/api-offline";
import { PageHeader } from "@/components/layout/page";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Td, Th } from "@/components/ui/table";
import { api, ApiError } from "@/lib/api";
import { appById, projectById } from "@/lib/projects";
import { requireOrg } from "@/lib/session";
import { hostsOf } from "@/lib/source-hosts";
import { DeployPanel } from "./deploy-panel";
import { PushButton } from "./push-button";
import { ReleasePanel } from "./release-panel";
import { SyncButton } from "./sync-button";

export default async function AppPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project: projectId, app: appId } = await params;
  const { org } = await requireOrg();
  const owner = await projectById(org.id, projectId);
  if (!owner) notFound();
  const app = await appById(projectId, appId);
  if (!app) notFound();
  const id = app.registryId;
  const hosts = await hostsOf(org.id);

  let data;
  try {
    const [project, gitflow, commits, branches, tags] = await Promise.all([
      api.apps.get(id),
      api.apps.gitflow(id),
      api.apps.commits(id, 15),
      api.apps.branches(id),
      api.apps.tags(id),
    ]);
    data = { project, gitflow, commits, branches, tags };
  } catch (e) {
    if (e instanceof ApiError && (e.status === 400 || e.status === 410)) notFound();
    return <ApiOffline error={e} />;
  }

  const { project, gitflow, commits, branches, tags } = data;
  const meta = project.project;

  return (
    <>
      <div className="mb-4 text-xs text-secondary"><Link href="/projects" className="hover:text-foreground">Projects</Link> / <Link href={`/projects/${projectId}`} className="hover:text-foreground">{owner.name}</Link> / <span className="text-foreground">{app.name}</span></div>
      <PageHeader
        title={meta.name || app.name}
        description={project.url || "not pushed yet"}
        actions={
          <div className="flex gap-2 items-center">
            {project.url ? (
              <SyncButton projectId={projectId} registryId={id} />
            ) : (
              <PushButton projectId={projectId} appId={app.id} registryId={id} repo={project.source_host.repo ?? app.name} hosts={hosts} current={app.sourceHostId} />
            )}
            <Badge>{meta.type ?? "?"}</Badge>
            <Badge>{meta.language ?? "?"}</Badge>
            {meta.ci && <Badge>ci: {meta.ci}</Badge>}
          </div>
        }
      />

      <div className="grid gap-4 md:grid-cols-4 mb-6">
        <Stat label="branch" value={<code className="font-mono">{project.branch}</code>} />
        <Stat label="LAST_VERSION" value={project.last_version ?? "—"} />
        <Stat label="latest tag" value={project.latest_tag ?? "—"} />
        <Stat label="working tree" value={<Badge tone={project.clean ? "ok" : "bad"}>{project.clean ? "clean" : "dirty"}</Badge>} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2 mb-6">
        <Card>
          <CardHeader>
            <CardTitle>Git-flow</CardTitle>
            <Badge tone={gitflow.ok ? "ok" : "bad"}>{gitflow.ok ? "ok" : `${gitflow.problems.length} problem(s)`}</Badge>
          </CardHeader>
          <CardContent className="text-sm">
            <div className="text-muted-foreground mb-2">{gitflow.checked_commits} commits checked on <code className="font-mono">{gitflow.branch}</code></div>
            {gitflow.problems.length > 0 && (
              <ul className="list-disc pl-5 space-y-1 text-foreground">
                {gitflow.problems.map((p) => <li key={p}>{p}</li>)}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Source & deploy</CardTitle></CardHeader>
          <CardContent className="text-sm space-y-1">
            <Row k="source_host" v={project.source_host.kind ? `${project.source_host.kind} · ${project.source_host.repo}` : "—"} />
            <Row k="release" v={project.release.strategy ? `${project.release.strategy} · ${project.release.changelog}` : "—"} />
            <Row k="deploy" v={Object.keys(project.deploy).length ? JSON.stringify(project.deploy) : "none"} />
            <Row k="services" v={Object.keys(project.services).length ? Object.keys(project.services).join(", ") : "none"} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2 mb-6">
        <ReleasePanel projectId={projectId} appId={app.id} registryId={id} branch={project.branch} />
        <DeployPanel projectId={projectId} registryId={id} hasTarget={Object.keys(project.deploy).length > 0} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3 mb-6">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Commits</CardTitle></CardHeader>
          <Table>
            <tbody>
              {commits.map((c) => (
                <tr key={c.sha}>
                  <Td className="font-mono text-xs text-muted-foreground w-20">{c.sha}</Td>
                  <Td>{c.subject}</Td>
                  <Td className="text-muted-foreground text-xs whitespace-nowrap">{c.date}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle>Branches</CardTitle></CardHeader>
            <Table>
              <tbody>
                {branches.map((b) => (
                  <tr key={b.name}>
                    <Td className="font-mono text-xs">{b.name}</Td>
                    <Td className="text-right">
                      {b.protected ? <Badge>protected</Badge> : b.problem ? <Badge tone="bad">not git-flow</Badge> : <Badge tone="ok">{b.kind}</Badge>}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </Card>
          <Card>
            <CardHeader><CardTitle>Tags</CardTitle></CardHeader>
            <CardContent className="flex flex-wrap gap-1">
              {tags.length === 0 && <span className="text-sm text-muted-foreground">none</span>}
              {tags.slice(0, 12).map((t) => <Badge key={t} className="font-mono">{t}</Badge>)}
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <Card className="p-4">
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      <div className="text-sm">{value}</div>
    </Card>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex gap-3">
      <span className="w-24 shrink-0 text-muted-foreground">{k}</span>
      <span className="font-mono text-xs break-all">{v}</span>
    </div>
  );
}
