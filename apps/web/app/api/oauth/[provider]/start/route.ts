import { redirect } from "next/navigation";
import { authorizeUrl, isConfigured, type Provider, PROVIDERS, signState } from "@/lib/oauth";
import { publicOrigin } from "@/lib/origin";
import { safePath } from "@/lib/safe-path";
import { isMember, roleOf } from "@/lib/orgs";
import { can } from "@/lib/permissions";
import { getSession } from "@/lib/session";
import { setupStatus } from "@/lib/setup";

export async function GET(req: Request, ctx: { params: Promise<{ provider: string }> }) {
  const { provider } = await ctx.params;
  if (!(provider in PROVIDERS)) return Response.json({ detail: "unknown provider" }, { status: 404 });
  if (!isConfigured(provider as Provider)) return Response.json({ detail: `${PROVIDERS[provider as Provider].label} OAuth app is not configured` }, { status: 400 });

  const url = new URL(req.url);
  const returnTo = safePath(url.searchParams.get("return"), "/settings");
  let orgId: string | null = null;

  const session = await getSession();
  if (session) {
    const requested = url.searchParams.get("org");
    orgId = requested && (await isMember(session.user.id, requested)) ? requested : (session.session.activeOrganizationId ?? null);
    if (orgId && !can(await roleOf(session.user.id, orgId), "org.manage")) return Response.json({ detail: "only owners and admins can connect code hosts" }, { status: 403 });
  } else {
    const status = await setupStatus();
    if (status.complete) redirect("/login");
    orgId = url.searchParams.get("org");
  }

  if (!orgId) return Response.json({ detail: "no organization" }, { status: 400 });

  const state = signState({ orgId, returnTo, userId: session?.user.id ?? null });
  redirect(authorizeUrl(provider as Provider, publicOrigin(req.headers), state));
}
