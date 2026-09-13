import { eq } from "drizzle-orm";
import { q } from "./db/query";
import { membersOf, orgsOf, roleOf } from "./orgs";
import { grantableScopes, grantsOf, ROLE_INFO, type Scope } from "./permissions";
import { appsOf, projectsOf } from "./projects";
import { teamsOf } from "./teams";

export async function organizationsOf(userId: string) {
  const orgs = await orgsOf(userId);
  return Promise.all(
    orgs.map(async (o) => {
      const role = await roleOf(userId, o.id);
      return { id: o.id, name: o.name, slug: o.slug, role, role_label: role ? ROLE_INFO[role]?.label ?? role : null, permissions: grantsOf(role), grantable_scopes: grantableScopes(role) };
    }),
  );
}

export async function projectsDirectory(orgId: string, projectId: string | null, appId: string | null) {
  const projects = await projectsOf(orgId);
  const visible = projectId ? projects.filter((p) => p.id === projectId) : projects;
  return Promise.all(
    visible.map(async (p) => {
      const apps = (await appsOf(p.id)).filter((a) => !appId || a.id === appId);
      return { id: p.id, name: p.name, slug: p.slug, description: p.description, team: p.teamId ? { id: p.teamId, name: p.teamName } : null, apps: apps.map((a) => ({ id: a.id, name: a.name, registry_id: a.registryId, source_host_id: a.sourceHostId, last_synced_at: a.lastSyncedAt })) };
    }),
  );
}

export async function teamsDirectory(orgId: string) {
  const { db, t } = await q();
  const teams = await teamsOf(orgId);
  return Promise.all(
    teams.map(async (team) => {
      const members = await db.select({ userId: t.teamMember.userId, name: t.user.name, email: t.user.email }).from(t.teamMember).innerJoin(t.user, eq(t.teamMember.userId, t.user.id)).where(eq(t.teamMember.teamId, team.id));
      const projects = await db.select({ id: t.project.id, name: t.project.name }).from(t.project).where(eq(t.project.teamId, team.id));
      return { id: team.id, name: team.name, slug: team.slug, description: team.description, members, projects };
    }),
  );
}

export async function membersDirectory(orgId: string) {
  return (await membersOf(orgId)).map((m) => ({ user_id: m.userId, name: m.name, email: m.email, role: m.role, role_label: ROLE_INFO[m.role as keyof typeof ROLE_INFO]?.label ?? m.role }));
}

export type Effective = { role: string | null; permissions: Record<string, boolean>; scope: Scope[] | null };
