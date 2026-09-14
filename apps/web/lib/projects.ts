import { and, asc, count, desc, eq } from "drizzle-orm";
import { newId, q } from "./db/query";
import { slugify } from "./utils";

export type Project = { id: string; organizationId: string; name: string; slug: string; description: string | null; teamId: string | null; teamName: string | null; createdAt: Date; apps: number };
export type App = { id: string; projectId: string; registryId: string; name: string; sourceHostId: string | null; lastSyncedAt: Date | null; createdAt: Date };

export async function projectsOf(orgId: string, id: string | null = null): Promise<Project[]> {
  const { db, t } = await q();
  const rows = await db
    .select({
      id: t.project.id,
      organizationId: t.project.organizationId,
      name: t.project.name,
      slug: t.project.slug,
      description: t.project.description,
      teamId: t.project.teamId,
      teamName: t.team.name,
      createdAt: t.project.createdAt,
      apps: count(t.app.id),
    })
    .from(t.project)
    .leftJoin(t.app, eq(t.app.projectId, t.project.id))
    .leftJoin(t.team, eq(t.project.teamId, t.team.id))
    .where(id ? and(eq(t.project.organizationId, orgId), eq(t.project.id, id)) : eq(t.project.organizationId, orgId))
    .groupBy(t.project.id, t.project.organizationId, t.project.name, t.project.slug, t.project.description, t.project.teamId, t.team.name, t.project.createdAt)
    .orderBy(asc(t.project.name));
  return rows.map((r) => ({ ...r, apps: Number(r.apps) }));
}

export async function projectById(orgId: string, id: string): Promise<Project | null> {
  const rows = await projectsOf(orgId, id);
  return rows[0] ?? null;
}

export async function createProject(orgId: string, name: string, description: string): Promise<Project> {
  const { db, t } = await q();
  const id = newId();
  const slug = slugify(name);
  await db.insert(t.project).values({ id, organizationId: orgId, name, slug, description: description || null, createdAt: new Date() });
  return { id, organizationId: orgId, name, slug, description: description || null, teamId: null, teamName: null, createdAt: new Date(), apps: 0 };
}

export async function deleteProject(orgId: string, id: string): Promise<string[]> {
  const { db, t } = await q();
  const owned = await projectById(orgId, id);
  if (!owned) return [];
  const apps = await appsOf(id);
  await db.delete(t.project).where(and(eq(t.project.id, id), eq(t.project.organizationId, orgId)));
  return apps.map((a) => a.registryId);
}

export async function appsOf(projectId: string): Promise<App[]> {
  const { db, t } = await q();
  return db.select().from(t.app).where(eq(t.app.projectId, projectId)).orderBy(desc(t.app.createdAt));
}

export async function appById(projectId: string, id: string): Promise<App | null> {
  const { db, t } = await q();
  const rows = await db.select().from(t.app).where(and(eq(t.app.id, id), eq(t.app.projectId, projectId))).limit(1);
  return rows[0] ?? null;
}

export async function createApp(projectId: string, registryId: string, name: string, sourceHostId: string | null = null): Promise<App> {
  const { db, t } = await q();
  const id = newId();
  const createdAt = new Date();
  await db.insert(t.app).values({ id, projectId, registryId, name, sourceHostId, lastSyncedAt: null, createdAt });
  return { id, projectId, registryId, name, sourceHostId, lastSyncedAt: null, createdAt };
}

export async function markSynced(projectId: string, id: string): Promise<void> {
  const { db, t } = await q();
  await db.update(t.app).set({ lastSyncedAt: new Date() }).where(and(eq(t.app.id, id), eq(t.app.projectId, projectId)));
}

export async function setAppHost(projectId: string, id: string, sourceHostId: string | null): Promise<void> {
  const { db, t } = await q();
  await db.update(t.app).set({ sourceHostId }).where(and(eq(t.app.id, id), eq(t.app.projectId, projectId)));
}

export async function deleteApp(projectId: string, id: string): Promise<App | null> {
  const { db, t } = await q();
  const app = await appById(projectId, id);
  if (!app) return null;
  await db.delete(t.app).where(eq(t.app.id, id));
  return app;
}

export async function appByRegistryId(registryId: string): Promise<(App & { organizationId: string }) | null> {
  const { db, t } = await q();
  const rows = await db
    .select({ id: t.app.id, projectId: t.app.projectId, registryId: t.app.registryId, name: t.app.name, sourceHostId: t.app.sourceHostId, lastSyncedAt: t.app.lastSyncedAt, createdAt: t.app.createdAt, organizationId: t.project.organizationId })
    .from(t.app)
    .innerJoin(t.project, eq(t.app.projectId, t.project.id))
    .where(eq(t.app.registryId, registryId))
    .limit(1);
  return rows[0] ?? null;
}
