import { sessionCookie } from "./auth";
import { authApi } from "./auth-api";

export type BrowserSession = { id: string; createdAt: Date; updatedAt: Date; expiresAt: Date; ipAddress: string | null; userAgent: string | null; current: boolean };

async function current(): Promise<{ cookie: string }> {
  const cookie = await sessionCookie();
  if (!cookie) throw new Error("sign in first");
  return { cookie };
}

export async function sessionsOf(): Promise<BrowserSession[]> {
  const rows = await authApi.sessions(await current());
  return rows.map((r) => ({ id: r.id, createdAt: new Date(r.created_at), updatedAt: new Date(r.updated_at), expiresAt: new Date(r.expires_at), ipAddress: r.ip_address ?? null, userAgent: r.user_agent ?? null, current: r.current }));
}

export async function revokeSession(id: string): Promise<boolean> {
  try {
    await authApi.revokeSession(await current(), id);
    return true;
  } catch (e) {
    if (e instanceof Error && "status" in e && (e as { status: number }).status === 404) return false;
    throw e;
  }
}
