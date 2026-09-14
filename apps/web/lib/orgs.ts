import { type Session, sessionCookie } from "./auth";
import { authApi } from "./auth-api";
import { type Role, ROLES } from "./permissions";
import { getSession } from "./session";
import type { Org } from "./types";
import { v1 } from "./v1";
import { slugify } from "./utils";

export type { Org, Role };
export { ROLES };

export async function orgsOf(_userId?: string): Promise<Org[]> {
  const session = await getSession();
  return (session?.organizations ?? []).map((o) => ({ id: o.id, name: o.name, slug: o.slug }));
}

export async function isMember(_userId: string, orgId: string): Promise<boolean> {
  return (await orgsOf()).some((o) => o.id === orgId);
}

export async function roleOf(_userId: string, orgId: string): Promise<Role | null> {
  const rows = await v1.organizations();
  const role = rows.find((o) => o.id === orgId)?.role ?? null;
  return role && (ROLES as readonly string[]).includes(role) ? (role as Role) : null;
}

export async function activeOrg(session: Session): Promise<Org | null> {
  const org = session.organization;
  return org ? { id: org.id, name: org.name, slug: org.slug } : null;
}

async function current(): Promise<{ cookie: string }> {
  const cookie = await sessionCookie();
  if (!cookie) throw new Error("sign in first");
  return { cookie };
}

export async function setActiveOrg(organizationId: string): Promise<void> {
  await authApi.setActiveOrganization(await current(), organizationId);
}

export async function createOrg(name: string, slug?: string): Promise<Org> {
  const org = await authApi.createOrganization(await current(), { name, slug: slug || slugify(name) });
  return { id: org.id, name: org.name, slug: org.slug };
}

export type Member = { id: string; userId: string; role: string; name: string; email: string };

export async function membersOf(_orgId: string): Promise<Member[]> {
  return (await v1.members()).map((m) => ({ id: m.user_id, userId: m.user_id, role: m.role, name: m.name, email: m.email }));
}

export type Invitation = { id: string; email: string; role: string | null; status: string; expiresAt: Date; createdAt: Date; inviter: string };

export async function invitationsOf(_orgId: string): Promise<Invitation[]> {
  return (await v1.invitations()).map((i) => ({ id: i.id, email: i.email, role: i.role ?? null, status: i.status, expiresAt: new Date(i.expires_at), createdAt: new Date(i.created_at), inviter: i.inviter }));
}

export type OpenInvitation = { id: string; email: string; role: string; org: Org; inviter: string; expired: boolean; status: string };

export async function invitationById(id: string): Promise<OpenInvitation | null> {
  try {
    const i = await authApi.openInvitation(id);
    return { id: i.id, email: i.email, role: i.role, org: { id: i.organization.id, name: i.organization.name, slug: i.organization.slug }, inviter: i.inviter, expired: i.expired, status: i.status };
  } catch (e) {
    if (e instanceof Error && "status" in e && (e as { status: number }).status === 404) return null;
    throw e;
  }
}

export async function acceptInvitation(id: string): Promise<Org> {
  const org = await authApi.acceptInvitation(await current(), id);
  return { id: org.id, name: org.name, slug: org.slug };
}
