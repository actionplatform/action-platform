import { and, asc, count, desc, eq } from "drizzle-orm";
import { newId, q } from "./db/query";
import { slugify } from "./utils";

export type Project = { id: string; organizationId: string; name: string; slug: string; description: string | null; createdAt: Date; apps: number };
export type App = { id: string; projectId: string; registryId: string; name: string; sourceHostId: string | null; createdAt: Date };

export async function projectsOf(orgId: string): Promise<Project[]> {
  const { db, t } = await q();
  const rows = await db
    .select({
      id: t.project.id,
      organizationId: t.project.organizationId,
      name: t.project.name,
      slug: t.project.slug,
      description: t.project.description,
      createdAt: t.project.createdAt,
      apps: count(t.app.id),
    })
    .from(t.project)
    .leftJoin(t.app, eq(t.app.projectId, t.project.id))
    .where(eq(t.project.organizationId, orgId))
    .groupBy(t.project.id, t.project.organizationId, t.project.name, t.project.slug, t.project.description, t.project.createdAt)
    .orderBy(asc(t.project.name));
  return rows.map((r) => ({ ...r, apps: Number(r.apps) }));
}

export async function projectById(orgId: string, id: string): Promise<Project | null> {
  const rows = (await projectsOf(orgId)).filter((p) => p.id === id);
  return rows[0] ?? null;
}

export async function createProject(orgId: string, name: string, description: string): Promise<Project> {
  const { db, t } = await q();
  const id = newId();
  const slug = slugify(name);
  await db.insert(t.project).values({ id, organizationId: orgId, name, slug, description: description || null, createdAt: new Date() });
  return { id, organizationId: orgId, name, slug, description: description || null, createdAt: new Date(), apps: 0 };
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
  await db.insert(t.app).values({ id, projectId, registryId, name, sourceHostId, createdAt });
  return { id, projectId, registryId, name, sourceHostId, createdAt };
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
