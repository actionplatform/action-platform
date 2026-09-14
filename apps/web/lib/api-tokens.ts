import { sessionCookie } from "./auth";
import { authApi, type GrantIn, isAuthError, type TokenRow } from "./auth-api";
import { parseScopes, type Scope } from "./permissions";

export type Reach = { projectId: string | null; appId: string | null };
export type TokenClient = { name: string; product: string; version: string | null; firstSeenAt: Date; lastSeenAt: Date };
export type UserToken = Reach & {
  id: string;
  name: string;
  scope: Scope[];
  createdAt: Date;
  expiresAt: Date;
  lastUsedAt: Date | null;
  clients: TokenClient[];
  organization: { id: string; name: string } | null;
  project: { id: string; name: string } | null;
  app: { id: string; name: string } | null;
};

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

export function looksLikeJwt(token: string): boolean {
  return token.split(".").length === 3;
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

export function toGrantIn(grant: Grant): GrantIn {
  return { scope: grant.scope, organization_id: grant.organizationId, project_id: grant.projectId, app_id: grant.appId };
}

async function current(): Promise<{ cookie: string }> {
  const cookie = await sessionCookie();
  if (!cookie) throw new Error("sign in first");
  return { cookie };
}

function fromRow(r: TokenRow): UserToken {
  return {
    id: r.id,
    name: r.name,
    scope: parseScopes(r.scope.join(" ")),
    projectId: r.project?.id ?? null,
    appId: r.app?.id ?? null,
    createdAt: new Date(r.created_at),
    expiresAt: new Date(r.expires_at),
    lastUsedAt: r.last_used_at ? new Date(r.last_used_at) : null,
    clients: r.clients.map((c) => ({ name: c.name, ...describeClient(c.name), firstSeenAt: new Date(c.first_seen_at), lastSeenAt: new Date(c.last_seen_at) })),
    organization: r.organization ?? null,
    project: r.project ?? null,
    app: r.app ?? null,
  };
}

export async function tokensOfUser(): Promise<UserToken[]> {
  return (await authApi.tokens(await current())).map(fromRow);
}

export async function revokeToken(id: string): Promise<boolean> {
  try {
    await authApi.revokeToken(await current(), id);
    return true;
  } catch (e) {
    if (isAuthError(e, 404)) return false;
    throw e;
  }
}

export async function deviceRequest(userCode: string): Promise<{ status: string; requested: Scope[]; grant: Grant; clientId: string | null; expiresAt: Date } | null> {
  try {
    const r = await authApi.deviceRequest(await current(), userCode);
    return {
      status: r.status,
      requested: parseScopes(r.requested.join(" ")),
      grant: { scope: parseScopes((r.grant.scope ?? []).join(" ")), organizationId: r.grant.organization_id ?? null, projectId: r.grant.project_id ?? null, appId: r.grant.app_id ?? null },
      clientId: r.client_id ?? null,
      expiresAt: new Date(r.expires_at),
    };
  } catch (e) {
    if (isAuthError(e, 404)) return null;
    throw e;
  }
}

export async function approveDevice(userCode: string, grant: Grant): Promise<void> {
  await authApi.deviceApprove(await current(), userCode, toGrantIn(grant));
}

export async function denyDevice(userCode: string): Promise<void> {
  await authApi.deviceDeny(await current(), userCode);
}
