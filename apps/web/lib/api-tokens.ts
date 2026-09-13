import { and, eq, inArray, isNull } from "drizzle-orm";
import { jwtVerify, SignJWT } from "jose";
import { readConfig } from "./config";
import { q } from "./db/query";
import { type Scope, parseScopes } from "./permissions";

export const TOKEN_TTL_DAYS = 90;
const ISSUER = "action-platform";

export type Reach = { projectId: string | null; appId: string | null };
export type ApiToken = Reach & { id: string; name: string; scope: Scope[]; createdAt: Date; expiresAt: Date; lastUsedAt: Date | null; revokedAt: Date | null };
export type TokenClaims = Reach & { id: string; userId: string; organizationId: string | null; scope: Scope[] };

function key(): Uint8Array {
  return new TextEncoder().encode(readConfig().authSecret);
}

export async function issueToken(input: { userId: string; organizationId: string | null; scope: Scope[]; name: string; projectId?: string | null; appId?: string | null }): Promise<{ token: string; id: string; expiresAt: Date }> {
  const { db, t } = await q();
  const id = crypto.randomUUID();
  const now = new Date();
  const expiresAt = new Date(now.getTime() + TOKEN_TTL_DAYS * 86400_000);
  await db.insert(t.apiToken).values({ id, userId: input.userId, organizationId: input.organizationId, name: input.name, scope: input.scope.join(" "), projectId: input.projectId ?? null, appId: input.appId ?? null, createdAt: now, expiresAt, lastUsedAt: null, revokedAt: null });
  const token = await new SignJWT({ org: input.organizationId ?? undefined, scope: input.scope.join(" "), project: input.projectId ?? undefined, app: input.appId ?? undefined })
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

export async function verifyToken(token: string, client: string | null = null): Promise<TokenClaims | null> {
  let payload;
  try {
    payload = (await jwtVerify(token, key(), { issuer: ISSUER })).payload;
  } catch {
    return null;
  }
  if (!payload.jti || !payload.sub) return null;

  const { db, t } = await q();
  const rows = await db.select().from(t.apiToken).where(and(eq(t.apiToken.id, payload.jti), isNull(t.apiToken.revokedAt))).limit(1);
  const row = rows[0];
  if (!row || row.userId !== payload.sub || (row.organizationId ?? null) !== ((payload.org as string | undefined) ?? null)) return null;
  if (row.expiresAt.getTime() < Date.now()) return null;

  const used = row.lastUsedAt?.getTime() ?? 0;
  if (Date.now() - used > 60_000) await db.update(t.apiToken).set({ lastUsedAt: new Date() }).where(eq(t.apiToken.id, row.id));
  if (client) await noteClient(row.id, client);

  return { id: row.id, userId: row.userId, organizationId: row.organizationId, scope: parseScopes(row.scope), projectId: row.projectId, appId: row.appId };
}

export type TokenClient = { name: string; product: string; version: string | null; firstSeenAt: Date; lastSeenAt: Date };

const KNOWN: [RegExp, string][] = [
  [/claude/i, "Claude Code"],
  [/codex/i, "Codex"],
  [/cursor/i, "Cursor"],
  [/windsurf/i, "Windsurf"],
  [/copilot/i, "GitHub Copilot"],
  [/gemini/i, "Gemini CLI"],
  [/cline/i, "Cline"],
  [/zed/i, "Zed"],
  [/vscode|visual studio code/i, "VS Code"],
  [/action-platform-cli/i, "action-platform CLI"],
];

export function describeClient(name: string): { product: string; version: string | null } {
  const [raw, version] = name.split("/", 2);
  const product = KNOWN.find(([re]) => re.test(raw))?.[1] ?? raw;
  return { product, version: version || null };
}

async function noteClient(tokenId: string, name: string): Promise<void> {
  const { db, t } = await q();
  const rows = await db.select({ id: t.apiTokenClient.id, lastSeenAt: t.apiTokenClient.lastSeenAt }).from(t.apiTokenClient).where(and(eq(t.apiTokenClient.tokenId, tokenId), eq(t.apiTokenClient.name, name))).limit(1);
  const now = new Date();
  if (!rows[0]) {
    await db.insert(t.apiTokenClient).values({ id: crypto.randomUUID(), tokenId, name, firstSeenAt: now, lastSeenAt: now });
    return;
  }
  if (now.getTime() - rows[0].lastSeenAt.getTime() > 60_000) await db.update(t.apiTokenClient).set({ lastSeenAt: now }).where(eq(t.apiTokenClient.id, rows[0].id));
}

async function clientsOf(tokenIds: string[]): Promise<Map<string, TokenClient[]>> {
  const out = new Map<string, TokenClient[]>();
  if (tokenIds.length === 0) return out;
  const { db, t } = await q();
  const rows = await db.select().from(t.apiTokenClient).where(inArray(t.apiTokenClient.tokenId, tokenIds));
  for (const r of rows) {
    const list = out.get(r.tokenId) ?? [];
    list.push({ name: r.name, ...describeClient(r.name), firstSeenAt: r.firstSeenAt, lastSeenAt: r.lastSeenAt });
    out.set(r.tokenId, list.sort((a, b) => b.lastSeenAt.getTime() - a.lastSeenAt.getTime()));
  }
  return out;
}

export async function tokensOf(userId: string, organizationId: string): Promise<ApiToken[]> {
  const { db, t } = await q();
  const rows = await db.select().from(t.apiToken).where(and(eq(t.apiToken.userId, userId), eq(t.apiToken.organizationId, organizationId), isNull(t.apiToken.revokedAt)));
  return rows
    .filter((r) => r.expiresAt.getTime() > Date.now())
    .map((r) => ({ id: r.id, name: r.name, scope: parseScopes(r.scope), projectId: r.projectId, appId: r.appId, createdAt: r.createdAt, expiresAt: r.expiresAt, lastUsedAt: r.lastUsedAt, revokedAt: r.revokedAt }))
    .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
}

export async function revokeToken(userId: string, id: string): Promise<boolean> {
  const { db, t } = await q();
  const rows = await db.select({ id: t.apiToken.id }).from(t.apiToken).where(and(eq(t.apiToken.id, id), eq(t.apiToken.userId, userId))).limit(1);
  if (!rows[0]) return false;
  await db.update(t.apiToken).set({ revokedAt: new Date() }).where(eq(t.apiToken.id, id));
  return true;
}

export type Grant = { scope: Scope[]; organizationId: string | null; projectId: string | null; appId: string | null };

export function formatGrant(grant: Grant): string {
  const parts: string[] = [...grant.scope];
  if (grant.organizationId) parts.push(`org:${grant.organizationId}`);
  if (grant.projectId) parts.push(`project:${grant.projectId}`);
  if (grant.appId) parts.push(`app:${grant.appId}`);
  return parts.join(" ");
}

export function parseGrant(value: string | null | undefined): Grant {
  const grant: Grant = { scope: parseScopes(value), organizationId: null, projectId: null, appId: null };
  for (const part of (value ?? "").split(/[\s,]+/)) {
    const [key, id] = part.split(":", 2);
    if (!id) continue;
    if (key === "org") grant.organizationId = id;
    if (key === "project") grant.projectId = id;
    if (key === "app") grant.appId = id;
  }
  return grant;
}

export async function setDeviceGrant(userCode: string, grant: Grant): Promise<boolean> {
  const { db, t } = await q();
  const rows = await db.select({ id: t.deviceCode.id, status: t.deviceCode.status }).from(t.deviceCode).where(eq(t.deviceCode.userCode, userCode)).limit(1);
  const row = rows[0];
  if (!row || row.status !== "pending") return false;
  await db.update(t.deviceCode).set({ scope: formatGrant(grant) }).where(eq(t.deviceCode.id, row.id));
  return true;
}

export async function deviceRequest(userCode: string): Promise<{ status: string; grant: Grant; clientId: string | null; expiresAt: Date } | null> {
  const { db, t } = await q();
  const rows = await db.select({ status: t.deviceCode.status, scope: t.deviceCode.scope, clientId: t.deviceCode.clientId, expiresAt: t.deviceCode.expiresAt }).from(t.deviceCode).where(eq(t.deviceCode.userCode, userCode)).limit(1);
  const row = rows[0];
  if (!row) return null;
  return { status: row.expiresAt.getTime() < Date.now() ? "expired" : row.status, grant: parseGrant(row.scope), clientId: row.clientId, expiresAt: row.expiresAt };
}

export type UserToken = ApiToken & { clients: TokenClient[]; organization: { id: string; name: string } | null; project: { id: string; name: string } | null; app: { id: string; name: string } | null };

export async function tokensOfUser(userId: string): Promise<UserToken[]> {
  const { db, t } = await q();
  const rows = await db
    .select({ token: t.apiToken, orgId: t.organization.id, orgName: t.organization.name, projectName: t.project.name, appName: t.app.name })
    .from(t.apiToken)
    .leftJoin(t.organization, eq(t.apiToken.organizationId, t.organization.id))
    .leftJoin(t.project, eq(t.apiToken.projectId, t.project.id))
    .leftJoin(t.app, eq(t.apiToken.appId, t.app.id))
    .where(and(eq(t.apiToken.userId, userId), isNull(t.apiToken.revokedAt)));
  const live = rows.filter((r) => r.token.expiresAt.getTime() > Date.now());
  const clients = await clientsOf(live.map((r) => r.token.id));
  return live
    .map((r) => ({
      id: r.token.id,
      name: r.token.name,
      clients: clients.get(r.token.id) ?? [],
      scope: parseScopes(r.token.scope),
      projectId: r.token.projectId,
      appId: r.token.appId,
      createdAt: r.token.createdAt,
      expiresAt: r.token.expiresAt,
      lastUsedAt: r.token.lastUsedAt,
      revokedAt: r.token.revokedAt,
      organization: r.orgId ? { id: r.orgId, name: r.orgName ?? "deleted organization" } : null,
      project: r.token.projectId ? { id: r.token.projectId, name: r.projectName ?? "deleted project" } : null,
      app: r.token.appId ? { id: r.token.appId, name: r.appName ?? "deleted app" } : null,
    }))
    .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
}
