import { and, eq, gt } from "drizzle-orm";
import { q } from "./db/query";

export type BrowserSession = { id: string; token: string; createdAt: Date; updatedAt: Date; expiresAt: Date; ipAddress: string | null; userAgent: string | null; current: boolean };

export async function sessionsOf(userId: string, currentToken: string): Promise<BrowserSession[]> {
  const { db, t } = await q();
  const rows = await db.select().from(t.session).where(and(eq(t.session.userId, userId), gt(t.session.expiresAt, new Date())));
  return rows
    .map((r) => ({ id: r.id, token: r.token, createdAt: r.createdAt, updatedAt: r.updatedAt, expiresAt: r.expiresAt, ipAddress: r.ipAddress, userAgent: r.userAgent, current: r.token === currentToken }))
    .sort((a, b) => Number(b.current) - Number(a.current) || b.updatedAt.getTime() - a.updatedAt.getTime());
}

export async function revokeSession(userId: string, id: string): Promise<boolean> {
  const { db, t } = await q();
  const rows = await db.select({ id: t.session.id }).from(t.session).where(and(eq(t.session.id, id), eq(t.session.userId, userId))).limit(1);
  if (!rows[0]) return false;
  await db.delete(t.session).where(eq(t.session.id, id));
  return true;
}
