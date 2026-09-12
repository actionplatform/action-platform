import { redirect } from "next/navigation";
import { authorizeUrl, isConfigured, type Provider, PROVIDERS, signState } from "@/lib/oauth";
import { isMember } from "@/lib/orgs";
import { getSession } from "@/lib/session";
import { setupStatus } from "@/lib/setup";

export async function GET(req: Request, ctx: { params: Promise<{ provider: string }> }) {
  const { provider } = await ctx.params;
  if (!(provider in PROVIDERS)) return Response.json({ detail: "unknown provider" }, { status: 404 });
  if (!isConfigured(provider as Provider)) return Response.json({ detail: `${PROVIDERS[provider as Provider].label} OAuth app is not configured` }, { status: 400 });

  const url = new URL(req.url);
  const returnTo = url.searchParams.get("return") || "/settings";
  let orgId: string | null = null;

  const session = await getSession();
  if (session) {
    const requested = url.searchParams.get("org");
    orgId = requested && (await isMember(session.user.id, requested)) ? requested : (session.session.activeOrganizationId ?? null);
  } else {
    const status = await setupStatus();
    if (status.complete) redirect("/login");
    orgId = url.searchParams.get("org");
  }

  if (!orgId) return Response.json({ detail: "no organization" }, { status: 400 });

  const state = signState({ orgId, returnTo });
  redirect(authorizeUrl(provider as Provider, url.origin, state));
}
