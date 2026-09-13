import { redirect } from "next/navigation";
import { appFor, signState } from "@/lib/oauth";
import { isMember, roleOf } from "@/lib/orgs";
import { can } from "@/lib/permissions";
import { getSession } from "@/lib/session";

export async function GET(req: Request) {
  const app = appFor("github");
  if (!app?.slug) return Response.json({ detail: "GitHub App is not configured" }, { status: 400 });

  const session = await getSession();
  if (!session) redirect("/login?next=/settings");

  const url = new URL(req.url);
  const requested = url.searchParams.get("org");
  const orgId = requested && (await isMember(session.user.id, requested)) ? requested : (session.session.activeOrganizationId ?? null);
  if (!orgId) return Response.json({ detail: "no organization" }, { status: 400 });
  if (!can(await roleOf(session.user.id, orgId), "org.manage")) return Response.json({ detail: "only owners and admins can connect code hosts" }, { status: 403 });

  const state = signState({ orgId, returnTo: url.searchParams.get("return") || "/settings" });
  redirect(`https://github.com/apps/${app.slug}/installations/select_target?state=${encodeURIComponent(state)}`);
}
