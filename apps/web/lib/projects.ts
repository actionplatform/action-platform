import { type ProjectRow, v1 } from "./v1";

export type Project = { id: string; organizationId: string; name: string; slug: string; description: string | null; teamId: string | null; teamName: string | null; apps: number; updatedAt: string; tearingDown: boolean };
export type App = { id: string; projectId: string; registryId: string; name: string; sourceHostId: string | null; lastSyncedAt: Date | null };

function project(row: ProjectRow, orgId: string): Project {
  return { id: row.id, organizationId: row.organization?.id ?? orgId, name: row.name, slug: row.slug, description: row.description ?? null, teamId: row.team?.id ?? null, teamName: row.team?.name ?? null, apps: row.apps.length, updatedAt: row.updated_at ?? row.created_at ?? "", tearingDown: row.tearing_down ?? false };
}

function app(row: ProjectRow["apps"][number], projectId: string): App {
  return { id: row.id, projectId, registryId: row.registry_id, name: row.name, sourceHostId: row.source_host_id ?? null, lastSyncedAt: row.last_synced_at ? new Date(row.last_synced_at) : null };
}

export async function projectsOf(orgId: string): Promise<Project[]> {
  return (await v1.projects(orgId)).map((r) => project(r, orgId));
}

export async function projectById(orgId: string, id: string): Promise<Project | null> {
  const row = (await v1.projects()).find((p) => p.id === id);
  return row ? project(row, orgId) : null;
}

export async function appsOf(projectId: string): Promise<App[]> {
  const row = (await v1.projects()).find((p) => p.id === projectId);
  return row ? row.apps.map((a) => app(a, projectId)) : [];
}

export async function appById(projectId: string, id: string): Promise<App | null> {
  return (await appsOf(projectId)).find((a) => a.id === id) ?? null;
}
