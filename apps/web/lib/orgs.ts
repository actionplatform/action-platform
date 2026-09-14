import { and, asc, eq } from "drizzle-orm";
import { type Session, sessionCookie } from "./auth";
import { authApi } from "./auth-api";
import { newId, q } from "./db/query";
import { can, type Permission, type Role, ROLES } from "./permissions";
import { slugify } from "./utils";

import type { Org } from "./types";
export type { Org };

export async function orgsOf(userId: string): Promise<Org[]> {
  const { db, t } = await q();
  const rows = await db
    .select({ id: t.organization.id, name: t.organization.name, slug: t.organization.slug })
    .from(t.member)
    .innerJoin(t.organization, eq(t.member.organizationId, t.organization.id))
    .where(eq(t.member.userId, userId))
    .orderBy(asc(t.organization.name));
  return rows;
}

export async function isMember(userId: string, orgId: string): Promise<boolean> {
  const { db, t } = await q();
  const rows = await db.select({ id: t.member.id }).from(t.member).where(and(eq(t.member.userId, userId), eq(t.member.organizationId, orgId))).limit(1);
  return rows.length > 0;
}

export async function activeOrg(session: Session): Promise<Org | null> {
  const org = session.organization;
  return org ? { id: org.id, name: org.name, slug: org.slug } : null;
}

export async function setActiveOrg(organizationId: string): Promise<void> {
  const cookie = await sessionCookie();
  if (!cookie) throw new Error("sign in first");
  await authApi.setActiveOrganization({ cookie }, organizationId);
}

export async function createOrg(name: string, slug?: string): Promise<Org> {
  const cookie = await sessionCookie();
  if (!cookie) throw new Error("sign in first");
  const org = await authApi.createOrganization({ cookie }, { name, slug: slug || slugify(name) });
  return { id: org.id, name: org.name, slug: org.slug };
}

export async function membersOf(orgId: string) {
  const { db, t } = await q();
  return db
    .select({ id: t.member.id, userId: t.member.userId, role: t.member.role, name: t.user.name, email: t.user.email, createdAt: t.member.createdAt })
    .from(t.member)
    .innerJoin(t.user, eq(t.member.userId, t.user.id))
    .where(eq(t.member.organizationId, orgId))
    .orderBy(asc(t.member.createdAt));
}

export { newId };

export { type Role, ROLES };

export async function roleOf(userId: string, orgId: string): Promise<Role | null> {
  const { db, t } = await q();
  const rows = await db.select({ role: t.member.role }).from(t.member).where(and(eq(t.member.userId, userId), eq(t.member.organizationId, orgId))).limit(1);
  return (rows[0]?.role as Role) ?? null;
}

export async function requireManager(userId: string, orgId: string): Promise<Role> {
  return requirePermission(userId, orgId, "org.manage");
}

export async function requirePermission(userId: string, orgId: string, permission: Permission): Promise<Role> {
  const role = await roleOf(userId, orgId);
  if (!can(role, permission)) throw new Error(`your role (${role ?? "none"}) cannot ${PERMISSION_LABEL[permission]}`);
  return role as Role;
}

const PERMISSION_LABEL: Record<Permission, string> = {
  "org.manage": "manage the organization",
  "project.manage": "manage projects and apps",
  "app.release": "create releases",
  "app.configure": "change configuration",
  "app.flow": "work with branches and pull requests",
  "app.sync": "sync apps",
};

export async function setMemberRole(orgId: string, memberId: string, role: Role): Promise<void> {
  const { db, t } = await q();
  const [current] = await db.select({ id: t.member.id, role: t.member.role }).from(t.member).where(and(eq(t.member.id, memberId), eq(t.member.organizationId, orgId)));
  if (!current) throw new Error("member not found");
  if (current.role === "owner" && role !== "owner" && (await ownersOf(orgId)) <= 1) throw new Error("the organization needs at least one owner");
  await db.update(t.member).set({ role }).where(and(eq(t.member.id, memberId), eq(t.member.organizationId, orgId)));
}

export async function removeMember(orgId: string, memberId: string): Promise<void> {
  const { db, t } = await q();
  const [current] = await db.select({ id: t.member.id, role: t.member.role, userId: t.member.userId }).from(t.member).where(and(eq(t.member.id, memberId), eq(t.member.organizationId, orgId)));
  if (!current) throw new Error("member not found");
  if (current.role === "owner" && (await ownersOf(orgId)) <= 1) throw new Error("the organization needs at least one owner");
  const teams = await db.select({ id: t.team.id }).from(t.team).where(eq(t.team.organizationId, orgId));
  for (const team of teams) await db.delete(t.teamMember).where(and(eq(t.teamMember.teamId, team.id), eq(t.teamMember.userId, current.userId)));
  await db.delete(t.member).where(and(eq(t.member.id, memberId), eq(t.member.organizationId, orgId)));
}

async function ownersOf(orgId: string): Promise<number> {
  const { db, t } = await q();
  const rows = await db.select({ id: t.member.id }).from(t.member).where(and(eq(t.member.organizationId, orgId), eq(t.member.role, "owner")));
  return rows.length;
}

export type Invitation = { id: string; email: string; role: string | null; status: string; expiresAt: Date; createdAt: Date; inviter: string };

export async function invitationsOf(orgId: string): Promise<Invitation[]> {
  const { db, t } = await q();
  const rows = await db
    .select({ id: t.invitation.id, email: t.invitation.email, role: t.invitation.role, status: t.invitation.status, expiresAt: t.invitation.expiresAt, createdAt: t.invitation.createdAt, inviter: t.user.name })
    .from(t.invitation)
    .innerJoin(t.user, eq(t.invitation.inviterId, t.user.id))
    .where(and(eq(t.invitation.organizationId, orgId), eq(t.invitation.status, "pending")))
    .orderBy(asc(t.invitation.createdAt));
  return rows.filter((r) => r.expiresAt > new Date());
}

export async function createInvitation(orgId: string, inviterId: string, email: string, role: Role): Promise<Invitation> {
  const { db, t } = await q();
  const normalized = email.trim().toLowerCase();
  const already = await db
    .select({ id: t.member.id })
    .from(t.member)
    .innerJoin(t.user, eq(t.member.userId, t.user.id))
    .where(and(eq(t.member.organizationId, orgId), eq(t.user.email, normalized)))
    .limit(1);
  if (already.length) throw new Error("already a member");
  const pending = (await invitationsOf(orgId)).find((i) => i.email === normalized);
  if (pending) return pending;
  const now = new Date();
  const row = { id: newId(), organizationId: orgId, email: normalized, role, status: "pending", expiresAt: new Date(now.getTime() + 7 * 24 * 3600 * 1000), createdAt: now, inviterId: inviterId };
  await db.insert(t.invitation).values(row);
  const [inviter] = await db.select({ name: t.user.name }).from(t.user).where(eq(t.user.id, inviterId));
  return { id: row.id, email: row.email, role: row.role, status: row.status, expiresAt: row.expiresAt, createdAt: row.createdAt, inviter: inviter?.name ?? "" };
}

export async function cancelInvitation(orgId: string, id: string): Promise<void> {
  const { db, t } = await q();
  await db.update(t.invitation).set({ status: "canceled" }).where(and(eq(t.invitation.id, id), eq(t.invitation.organizationId, orgId)));
}

export type OpenInvitation = { id: string; email: string; role: string; org: Org; inviter: string; expired: boolean; status: string };

export async function invitationById(id: string): Promise<OpenInvitation | null> {
  const { db, t } = await q();
  const [row] = await db
    .select({ id: t.invitation.id, email: t.invitation.email, role: t.invitation.role, status: t.invitation.status, expiresAt: t.invitation.expiresAt, inviter: t.user.name, orgId: t.organization.id, orgName: t.organization.name, orgSlug: t.organization.slug })
    .from(t.invitation)
    .innerJoin(t.user, eq(t.invitation.inviterId, t.user.id))
    .innerJoin(t.organization, eq(t.invitation.organizationId, t.organization.id))
    .where(eq(t.invitation.id, id));
  if (!row) return null;
  return { id: row.id, email: row.email, role: row.role ?? "member", status: row.status, inviter: row.inviter, expired: row.expiresAt < new Date(), org: { id: row.orgId, name: row.orgName, slug: row.orgSlug } };
}

export async function acceptInvitation(id: string, userId: string, userEmail: string): Promise<Org> {
  const invitation = await invitationById(id);
  if (!invitation) throw new Error("invitation not found");
  if (invitation.status !== "pending") throw new Error(`invitation ${invitation.status}`);
  if (invitation.expired) throw new Error("invitation expired");
  if (invitation.email !== userEmail.toLowerCase()) throw new Error(`this invitation is for ${invitation.email}`);
  const { db, t } = await q();
  if (!(await isMember(userId, invitation.org.id))) {
    await db.insert(t.member).values({ id: newId(), organizationId: invitation.org.id, userId, role: invitation.role, createdAt: new Date() });
  }
  await db.update(t.invitation).set({ status: "accepted" }).where(eq(t.invitation.id, id));
  await setActiveOrg(invitation.org.id);
  return invitation.org;
}

export async function addMemberAccount(orgId: string, input: { name: string; email: string; password: string; role: Role }): Promise<{ userId: string; existed: boolean }> {
  const cookie = await sessionCookie();
  if (!cookie) throw new Error("sign in first");
  const added = await authApi.addMember({ cookie }, { organization_id: orgId, name: input.name, email: input.email, password: input.password, role: input.role });
  return { userId: added.user_id, existed: added.existed };
}
