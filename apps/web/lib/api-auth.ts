import { getAuth } from "./auth";
import { looksLikeJwt, verifyToken } from "./api-tokens";
import { activeOrg, orgsOf } from "./orgs";
import type { Scope } from "./permissions";
import { q } from "./db/query";
import { eq } from "drizzle-orm";
import type { Org } from "./types";

export type Caller = { user: { id: string; name: string; email: string }; org: Org | null; scope: Scope[] | null; tokenId: string | null; projectId: string | null; appId: string | null };

export async function authenticate(req: Request): Promise<Caller | null> {
  const header = req.headers.get("authorization") ?? "";
  const bearer = header.toLowerCase().startsWith("bearer ") ? header.slice(7).trim() : "";

  if (bearer && looksLikeJwt(bearer)) {
    const claims = await verifyToken(bearer);
    if (!claims) return null;
    const { db, t } = await q();
    const users = await db.select({ id: t.user.id, name: t.user.name, email: t.user.email }).from(t.user).where(eq(t.user.id, claims.userId)).limit(1);
    const user = users[0];
    if (!user) return null;
    const org = (await orgsOf(user.id)).find((o) => o.id === claims.organizationId) ?? null;
    return { user, org, scope: claims.scope, tokenId: claims.id, projectId: claims.projectId, appId: claims.appId };
  }

  const auth = await getAuth();
  const session = await auth.api.getSession({ headers: req.headers });
  if (!session) return null;
  return { user: { id: session.user.id, name: session.user.name, email: session.user.email }, org: await activeOrg(session), scope: null, tokenId: null, projectId: null, appId: null };
}
