import { authApi, isAuthError } from "./auth-api";
import { looksLikeJwt } from "./api-tokens";
import { fromIdentity, sessionFromCookie } from "./auth";
import { parseScopes, type Scope } from "./permissions";
import type { Org } from "./types";

export type Caller = { user: { id: string; name: string; email: string }; org: Org | null; orgs: Org[]; allOrgs: boolean; scope: Scope[] | null; tokenId: string | null; projectId: string | null; appId: string | null; sessionToken: string | null };

const COOKIE = "better-auth.session_token";

function cookieValue(req: Request): string | null {
  const raw = req.headers.get("cookie") ?? "";
  for (const part of raw.split(";")) {
    const [name, ...rest] = part.trim().split("=");
    if (name === `__Secure-${COOKIE}` || name === COOKIE) return rest.join("=");
  }
  return null;
}

export async function authenticate(req: Request): Promise<Caller | null> {
  const header = req.headers.get("authorization") ?? "";
  const bearer = header.toLowerCase().startsWith("bearer ") ? header.slice(7).trim() : "";

  if (bearer && looksLikeJwt(bearer)) {
    const client = (req.headers.get("x-action-platform-client") ?? "").trim().slice(0, 120) || null;
    try {
      const claims = await authApi.verifyToken(bearer, client);
      const orgs = claims.organizations.map((o) => ({ id: o.id, name: o.name, slug: o.slug }));
      const org = claims.organization ? { id: claims.organization.id, name: claims.organization.name, slug: claims.organization.slug } : null;
      return { user: claims.user, org, orgs, allOrgs: claims.all_organizations, scope: parseScopes(claims.scope.join(" ")), tokenId: claims.id, projectId: claims.project_id ?? null, appId: claims.app_id ?? null, sessionToken: null };
    } catch (e) {
      if (isAuthError(e, 401, 403)) return null;
      throw e;
    }
  }

  let session = null;
  if (bearer) {
    try {
      session = fromIdentity(await authApi.session({ token: bearer }));
    } catch (e) {
      if (!isAuthError(e, 401)) throw e;
    }
  }
  if (!session) session = await sessionFromCookie(cookieValue(req));
  if (!session) return null;
  const orgs = session.organizations.map((o) => ({ id: o.id, name: o.name, slug: o.slug }));
  const org = session.organization ? { id: session.organization.id, name: session.organization.name, slug: session.organization.slug } : null;
  return { user: session.user, org, orgs, allOrgs: false, scope: null, tokenId: null, projectId: null, appId: null, sessionToken: session.session.token };
}
