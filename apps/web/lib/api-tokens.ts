import { and, eq, isNull } from "drizzle-orm";
import { jwtVerify, SignJWT } from "jose";
import { readConfig } from "./config";
import { q } from "./db/query";
import { type Scope, parseScopes } from "./permissions";

export const TOKEN_TTL_DAYS = 90;
const ISSUER = "action-platform";

export type ApiToken = { id: string; name: string; scope: Scope[]; createdAt: Date; expiresAt: Date; lastUsedAt: Date | null; revokedAt: Date | null };
export type TokenClaims = { id: string; userId: string; organizationId: string; scope: Scope[] };

function key(): Uint8Array {
  return new TextEncoder().encode(readConfig().authSecret);
}

export async function issueToken(input: { userId: string; organizationId: string; scope: Scope[]; name: string }): Promise<{ token: string; id: string; expiresAt: Date }> {
  const { db, t } = await q();
  const id = crypto.randomUUID();
  const now = new Date();
  const expiresAt = new Date(now.getTime() + TOKEN_TTL_DAYS * 86400_000);
  await db.insert(t.apiToken).values({ id, userId: input.userId, organizationId: input.organizationId, name: input.name, scope: input.scope.join(" "), createdAt: now, expiresAt, lastUsedAt: null, revokedAt: null });
  const token = await new SignJWT({ org: input.organizationId, scope: input.scope.join(" ") })
    .setProtectedHeader({ alg: "HS256", typ: "JWT" })
    .setIssuer(ISSUER)
    .setSubject(input.userId)
    .setJti(id)
    .setIssuedAt(now)
    .setExpirationTime(expiresAt)
    .sign(key());
  return { token, id, expiresAt };
}

export function looksLikeJwt(token: string): boolean {
  return token.split(".").length === 3;
}

export async function verifyToken(token: string): Promise<TokenClaims | null> {
  let payload;
  try {
    payload = (await jwtVerify(token, key(), { issuer: ISSUER })).payload;
  } catch {
    return null;
  }
  if (!payload.jti || !payload.sub || typeof payload.org !== "string") return null;

  const { db, t } = await q();
  const rows = await db.select().from(t.apiToken).where(and(eq(t.apiToken.id, payload.jti), isNull(t.apiToken.revokedAt))).limit(1);
  const row = rows[0];
  if (!row || row.userId !== payload.sub || row.organizationId !== payload.org) return null;
  if (row.expiresAt.getTime() < Date.now()) return null;

  const used = row.lastUsedAt?.getTime() ?? 0;
  if (Date.now() - used > 60_000) await db.update(t.apiToken).set({ lastUsedAt: new Date() }).where(eq(t.apiToken.id, row.id));

  return { id: row.id, userId: row.userId, organizationId: row.organizationId, scope: parseScopes(row.scope) };
}

export async function tokensOf(userId: string, organizationId: string): Promise<ApiToken[]> {
  const { db, t } = await q();
  const rows = await db.select().from(t.apiToken).where(and(eq(t.apiToken.userId, userId), eq(t.apiToken.organizationId, organizationId), isNull(t.apiToken.revokedAt)));
  return rows
    .filter((r) => r.expiresAt.getTime() > Date.now())
    .map((r) => ({ id: r.id, name: r.name, scope: parseScopes(r.scope), createdAt: r.createdAt, expiresAt: r.expiresAt, lastUsedAt: r.lastUsedAt, revokedAt: r.revokedAt }))
    .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
}

export async function revokeToken(userId: string, id: string): Promise<boolean> {
  const { db, t } = await q();
  const rows = await db.select({ id: t.apiToken.id }).from(t.apiToken).where(and(eq(t.apiToken.id, id), eq(t.apiToken.userId, userId))).limit(1);
  if (!rows[0]) return false;
  await db.update(t.apiToken).set({ revokedAt: new Date() }).where(eq(t.apiToken.id, id));
  return true;
}

export async function setDeviceScope(userCode: string, scope: Scope[]): Promise<boolean> {
  const { db, t } = await q();
  const rows = await db.select({ id: t.deviceCode.id, status: t.deviceCode.status }).from(t.deviceCode).where(eq(t.deviceCode.userCode, userCode)).limit(1);
  const row = rows[0];
  if (!row || row.status !== "pending") return false;
  await db.update(t.deviceCode).set({ scope: scope.join(" ") }).where(eq(t.deviceCode.id, row.id));
  return true;
}

export async function deviceRequest(userCode: string): Promise<{ status: string; scope: Scope[]; clientId: string | null } | null> {
  const { db, t } = await q();
  const rows = await db.select({ status: t.deviceCode.status, scope: t.deviceCode.scope, clientId: t.deviceCode.clientId, expiresAt: t.deviceCode.expiresAt }).from(t.deviceCode).where(eq(t.deviceCode.userCode, userCode)).limit(1);
  const row = rows[0];
  if (!row || row.expiresAt.getTime() < Date.now()) return null;
  return { status: row.status, scope: parseScopes(row.scope), clientId: row.clientId };
}
