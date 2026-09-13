import { redirect } from "next/navigation";
import { exchangeCode, identity, type Provider, PROVIDERS, verifyState } from "@/lib/oauth";
import { publicOrigin } from "@/lib/origin";
import { activeOrg } from "@/lib/orgs";
import { getSession } from "@/lib/session";
import { connectOAuthHost } from "@/lib/source-hosts";

async function installationOwner(token: string, installationId: string): Promise<string | null> {
  try {
    const res = await fetch("https://api.github.com/user/installations", { headers: { authorization: `Bearer ${token}`, accept: "application/vnd.github+json", "user-agent": "action-platform" }, cache: "no-store" });
    if (!res.ok) return null;
    const data = (await res.json()) as { installations: { id: number; account: { login: string } }[] };
    return data.installations.find((i) => String(i.id) === installationId)?.account.login ?? null;
  } catch {
    return null;
  }
}

async function firstWorkspace(token: string): Promise<string | null> {
  try {
    const res = await fetch("https://api.bitbucket.org/2.0/user/permissions/workspaces?pagelen=100", { headers: { authorization: `Bearer ${token}`, accept: "application/json", "user-agent": "action-platform" }, cache: "no-store" });
    if (!res.ok) return null;
    const data = (await res.json()) as { values: { workspace: { slug: string }; permission: string }[] };
    const spaces = data.values ?? [];
    return (spaces.find((w) => w.permission === "owner") ?? spaces.find((w) => w.permission === "collaborator") ?? spaces[0])?.workspace.slug ?? null;
  } catch {
    return null;
  }
}

export async function GET(req: Request, ctx: { params: Promise<{ provider: string }> }) {
  const { provider } = await ctx.params;
  if (!(provider in PROVIDERS)) return Response.json({ detail: "unknown provider" }, { status: 404 });

  const url = new URL(req.url);
  const origin = publicOrigin(req.headers);
  const state = verifyState(url.searchParams.get("state"));
  const installed = provider === "github" && url.searchParams.has("installation_id");

  let orgId = state?.orgId ?? "";
  let returnTo = state?.returnTo ?? "/settings";

  if (!state) {
    if (!installed) return Response.json({ detail: "invalid or expired state" }, { status: 400 });
    const session = await getSession();
    if (!session) redirect(`/login?next=${encodeURIComponent(url.pathname + url.search)}`);
    const org = await activeOrg(session);
    if (!org) redirect("/orgs/new");
    orgId = org.id;
  }

  const back = (query: Record<string, string>) => {
    const target = new URL(returnTo, origin);
    for (const [k, v] of Object.entries(query)) target.searchParams.set(k, v);
    redirect(target.pathname + target.search);
  };

  const denied = url.searchParams.get("error");
  if (denied) return back({ oauth_error: url.searchParams.get("error_description") || denied });

  const code = url.searchParams.get("code");
  if (!code) return back({ oauth_error: "no code from the provider" });

  try {
    const tokens = await exchangeCode(provider as Provider, origin, code);
    const who = await identity(provider as Provider, tokens.accessToken);
    const installationId = url.searchParams.get("installation_id");
    const owner = installationId ? await installationOwner(tokens.accessToken, installationId) : provider === "bitbucket" ? await firstWorkspace(tokens.accessToken) : null;
    await connectOAuthHost(orgId, provider as Provider, who.login, tokens, owner);
  } catch (e) {
    return back({ oauth_error: (e as Error).message });
  }

  return back({ connected: provider });
}
