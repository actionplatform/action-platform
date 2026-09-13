import { getAuth } from "./auth";
import { looksLikeJwt, verifyToken } from "./api-tokens";
import { activeOrg, orgsOf } from "./orgs";
import type { Scope } from "./permissions";
import { q } from "./db/query";
import { eq } from "drizzle-orm";
import type { Org } from "./types";

export type Caller = { user: { id: string; name: string; email: string }; org: Org | null; orgs: Org[]; allOrgs: boolean; scope: Scope[] | null; tokenId: string | null; projectId: string | null; appId: string | null };

export async function authenticate(req: Request): Promise<Caller | null> {
  const header = req.headers.get("authorization") ?? "";
  const bearer = header.toLowerCase().startsWith("bearer ") ? header.slice(7).trim() : "";

  if (bearer && looksLikeJwt(bearer)) {
    const client = (req.headers.get("x-action-platform-client") ?? "").trim().slice(0, 120) || null;
    const claims = await verifyToken(bearer, client);
    if (!claims) return null;
    const { db, t } = await q();
    const users = await db.select({ id: t.user.id, name: t.user.name, email: t.user.email }).from(t.user).where(eq(t.user.id, claims.userId)).limit(1);
    const user = users[0];
    if (!user) return null;
    const orgs = await orgsOf(user.id);
    const org = claims.organizationId ? orgs.find((o) => o.id === claims.organizationId) ?? null : null;
    if (claims.organizationId && !org) return null;
    return { user, org, orgs, allOrgs: !claims.organizationId, scope: claims.scope, tokenId: claims.id, projectId: claims.projectId, appId: claims.appId };
  }

  const auth = await getAuth();
  const session = await auth.api.getSession({ headers: req.headers });
  if (!session) return null;
  const orgs = await orgsOf(session.user.id);
  return { user: { id: session.user.id, name: session.user.name, email: session.user.email }, org: await activeOrg(session), orgs, allOrgs: false, scope: null, tokenId: null, projectId: null, appId: null };
}
