import { and, asc, count, eq, inArray } from "drizzle-orm";
import { newId, q } from "./db/query";
import { slugify } from "./utils";

export type Team = { id: string; organizationId: string; name: string; slug: string; description: string | null; createdAt: Date; members: number; projects: number };
export type TeamMember = { id: string; userId: string; name: string; email: string; createdAt: Date };
export type TeamProject = { id: string; name: string; slug: string; description: string | null };

export async function teamsOf(orgId: string): Promise<Team[]> {
  const { db, t } = await q();
  const rows = await db.select().from(t.team).where(eq(t.team.organizationId, orgId)).orderBy(asc(t.team.name));
  if (rows.length === 0) return [];
  const ids = rows.map((r) => r.id);
  const members = await db.select({ teamId: t.teamMember.teamId, n: count(t.teamMember.id) }).from(t.teamMember).where(inArray(t.teamMember.teamId, ids)).groupBy(t.teamMember.teamId);
  const projects = await db.select({ teamId: t.project.teamId, n: count(t.project.id) }).from(t.project).where(inArray(t.project.teamId, ids)).groupBy(t.project.teamId);
  const m = new Map(members.map((r) => [r.teamId, Number(r.n)]));
  const p = new Map(projects.map((r) => [r.teamId, Number(r.n)]));
  return rows.map((r) => ({ ...r, members: m.get(r.id) ?? 0, projects: p.get(r.id) ?? 0 }));
}

export async function teamById(orgId: string, id: string): Promise<Team | null> {
  return (await teamsOf(orgId)).find((x) => x.id === id) ?? null;
}

export async function createTeam(orgId: string, name: string, description: string): Promise<Team> {
  const { db, t } = await q();
  const trimmed = name.trim();
  if (!trimmed) throw new Error("name is required");
  const slug = slugify(trimmed);
  const taken = await db.select({ id: t.team.id }).from(t.team).where(and(eq(t.team.organizationId, orgId), eq(t.team.slug, slug))).limit(1);
  if (taken.length) throw new Error(`a team named ${trimmed} already exists`);
  const row = { id: newId(), organizationId: orgId, name: trimmed, slug, description: description.trim() || null, createdAt: new Date() };
  await db.insert(t.team).values(row);
  return { ...row, members: 0, projects: 0 };
}

export async function updateTeam(orgId: string, id: string, name: string, description: string): Promise<void> {
  const { db, t } = await q();
  const trimmed = name.trim();
  if (!trimmed) throw new Error("name is required");
  await db.update(t.team).set({ name: trimmed, slug: slugify(trimmed), description: description.trim() || null }).where(and(eq(t.team.id, id), eq(t.team.organizationId, orgId)));
}

export async function deleteTeam(orgId: string, id: string): Promise<void> {
  const { db, t } = await q();
  await db.update(t.project).set({ teamId: null }).where(and(eq(t.project.organizationId, orgId), eq(t.project.teamId, id)));
  await db.delete(t.team).where(and(eq(t.team.id, id), eq(t.team.organizationId, orgId)));
}

export async function teamMembersOf(teamId: string): Promise<TeamMember[]> {
  const { db, t } = await q();
  return db
    .select({ id: t.teamMember.id, userId: t.teamMember.userId, name: t.user.name, email: t.user.email, createdAt: t.teamMember.createdAt })
    .from(t.teamMember)
    .innerJoin(t.user, eq(t.teamMember.userId, t.user.id))
    .where(eq(t.teamMember.teamId, teamId))
    .orderBy(asc(t.user.name));
}

export async function addTeamMember(orgId: string, teamId: string, userId: string): Promise<void> {
  const { db, t } = await q();
  const team = await teamById(orgId, teamId);
  if (!team) throw new Error("team not found");
  const member = await db.select({ id: t.member.id }).from(t.member).where(and(eq(t.member.organizationId, orgId), eq(t.member.userId, userId))).limit(1);
  if (!member.length) throw new Error("not a member of the organization");
  const exists = await db.select({ id: t.teamMember.id }).from(t.teamMember).where(and(eq(t.teamMember.teamId, teamId), eq(t.teamMember.userId, userId))).limit(1);
  if (exists.length) return;
  await db.insert(t.teamMember).values({ id: newId(), teamId, userId, createdAt: new Date() });
}

export async function removeTeamMember(orgId: string, teamId: string, id: string): Promise<void> {
  const { db, t } = await q();
  const team = await teamById(orgId, teamId);
  if (!team) throw new Error("team not found");
  await db.delete(t.teamMember).where(and(eq(t.teamMember.id, id), eq(t.teamMember.teamId, teamId)));
}

export async function projectsOfTeam(orgId: string, teamId: string): Promise<TeamProject[]> {
  const { db, t } = await q();
  return db
    .select({ id: t.project.id, name: t.project.name, slug: t.project.slug, description: t.project.description })
    .from(t.project)
    .where(and(eq(t.project.organizationId, orgId), eq(t.project.teamId, teamId)))
    .orderBy(asc(t.project.name));
}

export async function assignProjectTeam(orgId: string, projectId: string, teamId: string | null): Promise<void> {
  const { db, t } = await q();
  if (teamId && !(await teamById(orgId, teamId))) throw new Error("team not found");
  await db.update(t.project).set({ teamId }).where(and(eq(t.project.id, projectId), eq(t.project.organizationId, orgId)));
}
