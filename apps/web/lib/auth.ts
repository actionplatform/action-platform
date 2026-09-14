import { cookies, headers } from "next/headers";
import { authApi, type Identity, isAuthError } from "./auth-api";

const COOKIE = "better-auth.session_token";
const SECURE_COOKIE = `__Secure-${COOKIE}`;

function secure(): boolean {
  const base = process.env.PUBLIC_URL ?? process.env.BETTER_AUTH_URL ?? "";
  return base.startsWith("https://");
}

export async function sessionCookie(): Promise<string | null> {
  const jar = await cookies();
  return jar.get(SECURE_COOKIE)?.value ?? jar.get(COOKIE)?.value ?? null;
}

export async function setSessionCookie(cookie: string, expiresAt: string): Promise<void> {
  const jar = await cookies();
  jar.set(secure() ? SECURE_COOKIE : COOKIE, cookie, { httpOnly: true, sameSite: "lax", secure: secure(), path: "/", expires: new Date(expiresAt) });
}

export async function clearSessionCookie(): Promise<void> {
  const jar = await cookies();
  jar.delete(SECURE_COOKIE);
  jar.delete(COOKIE);
}

export async function requestClient(): Promise<{ ip: string | null; userAgent: string | null }> {
  const h = await headers();
  const forwarded = h.get("x-forwarded-for")?.split(",")[0]?.trim() || null;
  return { ip: forwarded ?? h.get("x-real-ip"), userAgent: h.get("user-agent") };
}

export type Session = {
  user: Identity["user"];
  session: { id: string; token: string; activeOrganizationId: string | null; expiresAt: string };
  organization: Identity["organization"];
  organizations: Identity["organizations"];
  role: string | null;
  grants: Record<string, boolean>;
};

export function fromIdentity(identity: Identity): Session {
  return {
    user: identity.user,
    session: { id: identity.session.id, token: identity.session.token, activeOrganizationId: identity.session.active_organization_id ?? null, expiresAt: identity.session.expires_at },
    organization: identity.organization ?? null,
    organizations: identity.organizations,
    role: identity.role ?? null,
    grants: identity.grants,
  };
}

export async function sessionFromCookie(cookie: string | null): Promise<Session | null> {
  if (!cookie) return null;
  try {
    return fromIdentity(await authApi.session({ cookie }));
  } catch (e) {
    if (isAuthError(e, 401)) return null;
    throw e;
  }
}
