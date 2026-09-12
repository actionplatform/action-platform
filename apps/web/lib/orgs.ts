import { and, asc, eq } from "drizzle-orm";
import { headers } from "next/headers";
import { getAuth } from "./auth";
import { newId, q } from "./db/query";
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

// The org the sidebar shows: the session's active one when it is still a
// membership, else the first membership (and the session is pointed at it).
export async function activeOrg(session: { user: { id: string }; session: { activeOrganizationId?: string | null } }): Promise<Org | null> {
  const orgs = await orgsOf(session.user.id);
  if (orgs.length === 0) return null;

  const active = orgs.find((o) => o.id === session.session.activeOrganizationId);
  if (active) return active;

  await setActiveOrg(orgs[0].id);
  return orgs[0];
}

export async function setActiveOrg(organizationId: string): Promise<void> {
  const auth = await getAuth();
  await auth.api.setActiveOrganization({ headers: await headers(), body: { organizationId } });
}

// Owner membership is written by better-auth on createOrganization.
export async function createOrg(name: string, slug?: string): Promise<Org> {
  const auth = await getAuth();
  const org = await auth.api.createOrganization({ headers: await headers(), body: { name, slug: slug || slugify(name) } });
  if (!org) throw new Error("could not create the organization");
  await setActiveOrg(org.id);
  return { id: org.id, name: org.name, slug: org.slug };
}

export async function membersOf(orgId: string) {
  const { db, t } = await q();
  return db
    .select({ id: t.member.id, role: t.member.role, name: t.user.name, email: t.user.email, createdAt: t.member.createdAt })
    .from(t.member)
    .innerJoin(t.user, eq(t.member.userId, t.user.id))
    .where(eq(t.member.organizationId, orgId))
    .orderBy(asc(t.member.createdAt));
}

export { newId };
