import { redirect } from "next/navigation";
import { type Provider, PROVIDERS } from "@/lib/oauth";
import { publicOrigin } from "@/lib/origin";
import { verifyInvitationFinish } from "@/lib/orgs";
import { failed } from "@/lib/result";
import { safePath } from "@/lib/safe-path";
import { getSession } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function GET(req: Request, ctx: { params: Promise<{ provider: string }> }) {
  const { provider } = await ctx.params;
  if (!(provider in PROVIDERS)) return Response.json({ detail: "unknown provider" }, { status: 404 });

  const url = new URL(req.url);
  const session = await getSession();
  if (!session) redirect(`/login?next=${encodeURIComponent(url.pathname + url.search)}`);

  const invite = /^invite\.([^.]+)\./.exec(url.searchParams.get("state") ?? "");
  if (invite) {
    const back = `/invite/${encodeURIComponent(invite[1])}`;
    const refused = url.searchParams.get("error_description") ?? url.searchParams.get("error");
    let error: string | null = refused;
    if (!refused) {
      try {
        await verifyInvitationFinish(invite[1], { origin: publicOrigin(req.headers), code: url.searchParams.get("code") ?? "", state: url.searchParams.get("state") ?? "" });
      } catch (e) {
        error = failed(e).error;
      }
    }
    redirect(error ? `${back}?error=${encodeURIComponent(error)}` : "/projects");
  }

  let finished: { return_to: string; query: Record<string, string> };
  try {
    finished = await v1.oauthCallback(provider as Provider, {
      origin: publicOrigin(req.headers),
      code: url.searchParams.get("code"),
      state: url.searchParams.get("state"),
      installation_id: url.searchParams.get("installation_id"),
      error: url.searchParams.get("error"),
      error_description: url.searchParams.get("error_description"),
    });
  } catch (e) {
    return Response.json({ detail: (e as Error).message }, { status: 400 });
  }

  const target = new URL(safePath(finished.return_to, "/connect/git"), publicOrigin(req.headers));
  for (const [k, v] of Object.entries(finished.query)) target.searchParams.set(k, v);
  redirect(target.pathname + target.search);
}
