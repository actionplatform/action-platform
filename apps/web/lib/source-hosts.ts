import { and, asc, eq } from "drizzle-orm";
import { decrypt, encrypt } from "./crypto";
import { newId, q } from "./db/query";
import { apiBaseUrl, type Provider, refreshToken } from "./oauth";

export { HOST_KINDS, type HostKind, type SourceHost } from "./source-host-kinds";
import type { HostKind, SourceHost } from "./source-host-kinds";

// What the Python API receives with a push / release call.
export type Credentials = { kind: string; token: string; username: string | null; base_url: string | null; owner: string | null };

const columns = (t: Awaited<ReturnType<typeof q>>["t"]) => ({
  id: t.sourceHost.id,
  organizationId: t.sourceHost.organizationId,
  kind: t.sourceHost.kind,
  name: t.sourceHost.name,
  baseUrl: t.sourceHost.baseUrl,
  username: t.sourceHost.username,
  defaultOwner: t.sourceHost.defaultOwner,
  authKind: t.sourceHost.authKind,
  login: t.sourceHost.login,
  createdAt: t.sourceHost.createdAt,
});

export async function hostsOf(orgId: string): Promise<SourceHost[]> {
  const { db, t } = await q();
  const rows = await db.select(columns(t)).from(t.sourceHost).where(eq(t.sourceHost.organizationId, orgId)).orderBy(asc(t.sourceHost.createdAt));
  return rows as SourceHost[];
}

export async function hostById(orgId: string, id: string): Promise<SourceHost | null> {
  const { db, t } = await q();
  const rows = await db.select(columns(t)).from(t.sourceHost).where(and(eq(t.sourceHost.id, id), eq(t.sourceHost.organizationId, orgId))).limit(1);
  return (rows[0] as SourceHost | undefined) ?? null;
}

export async function addHost(orgId: string, input: { kind: HostKind; name: string; baseUrl?: string; username?: string; token: string; defaultOwner?: string }): Promise<SourceHost> {
  const { db, t } = await q();
  const id = newId();
  const createdAt = new Date();
  await db.insert(t.sourceHost).values({
    id,
    organizationId: orgId,
    kind: input.kind,
    name: input.name,
    baseUrl: input.baseUrl || null,
    username: input.username || null,
    tokenEncrypted: encrypt(input.token),
    defaultOwner: input.defaultOwner || null,
    authKind: "token",
    login: null,
    createdAt,
  });
  return { id, organizationId: orgId, kind: input.kind, name: input.name, baseUrl: input.baseUrl || null, username: input.username || null, defaultOwner: input.defaultOwner || null, authKind: "token", login: null, createdAt };
}

// A host created by "Connect with…": the provider's user is the owner
// default, and the refresh token (when the provider issues one) keeps it
// alive. Reconnecting the same account replaces the tokens.
export async function connectOAuthHost(orgId: string, provider: Provider, login: string, tokens: { accessToken: string; refreshToken: string | null; expiresAt: Date | null }): Promise<SourceHost> {
  const { db, t } = await q();
  const existing = await db
    .select({ id: t.sourceHost.id })
    .from(t.sourceHost)
    .where(and(eq(t.sourceHost.organizationId, orgId), eq(t.sourceHost.kind, provider), eq(t.sourceHost.authKind, "oauth"), eq(t.sourceHost.login, login)))
    .limit(1);
  const values = {
    tokenEncrypted: encrypt(tokens.accessToken),
    refreshTokenEncrypted: tokens.refreshToken ? encrypt(tokens.refreshToken) : null,
    expiresAt: tokens.expiresAt,
    baseUrl: apiBaseUrl(provider),
  };

  if (existing[0]) {
    await db.update(t.sourceHost).set(values).where(eq(t.sourceHost.id, existing[0].id));
    return (await hostByIdAny(existing[0].id))!;
  }

  const id = newId();
  const createdAt = new Date();
  await db.insert(t.sourceHost).values({
    id,
    organizationId: orgId,
    kind: provider,
    name: `${provider === "github" ? "GitHub" : provider === "gitlab" ? "GitLab" : "Bitbucket"} · ${login}`,
    username: provider === "bitbucket" ? "x-token-auth" : null,
    defaultOwner: login,
    authKind: "oauth",
    login,
    createdAt,
    ...values,
  });
  return (await hostByIdAny(id))!;
}

async function hostByIdAny(id: string): Promise<SourceHost | null> {
  const { db, t } = await q();
  const rows = await db.select(columns(t)).from(t.sourceHost).where(eq(t.sourceHost.id, id)).limit(1);
  return (rows[0] as SourceHost | undefined) ?? null;
}

export async function updateHostToken(orgId: string, id: string, token: string): Promise<void> {
  const { db, t } = await q();
  await db.update(t.sourceHost).set({ tokenEncrypted: encrypt(token) }).where(and(eq(t.sourceHost.id, id), eq(t.sourceHost.organizationId, orgId)));
}

export async function removeHost(orgId: string, id: string): Promise<void> {
  const { db, t } = await q();
  await db.delete(t.sourceHost).where(and(eq(t.sourceHost.id, id), eq(t.sourceHost.organizationId, orgId)));
}

// The only place the token is decrypted: right before a call to the API.
// Expiring OAuth tokens are refreshed here when they have under a minute left.
export async function credentialsFor(orgId: string, id: string): Promise<Credentials | null> {
  const { db, t } = await q();
  const rows = await db.select().from(t.sourceHost).where(and(eq(t.sourceHost.id, id), eq(t.sourceHost.organizationId, orgId))).limit(1);
  const row = rows[0];
  if (!row) return null;

  let token = decrypt(row.tokenEncrypted);

  if (row.authKind === "oauth" && row.refreshTokenEncrypted && row.expiresAt && row.expiresAt.getTime() - Date.now() < 60_000) {
    const fresh = await refreshToken(row.kind as Provider, decrypt(row.refreshTokenEncrypted));
    await db
      .update(t.sourceHost)
      .set({ tokenEncrypted: encrypt(fresh.accessToken), refreshTokenEncrypted: fresh.refreshToken ? encrypt(fresh.refreshToken) : row.refreshTokenEncrypted, expiresAt: fresh.expiresAt })
      .where(eq(t.sourceHost.id, row.id));
    token = fresh.accessToken;
  }

  return { kind: row.kind, token, username: row.username, base_url: row.baseUrl, owner: row.defaultOwner };
}
