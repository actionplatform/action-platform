import { redirect } from "next/navigation";
import { type Provider, PROVIDERS } from "@/lib/oauth";
import { publicOrigin } from "@/lib/origin";
import { safePath } from "@/lib/safe-path";
import { getSession } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function GET(req: Request, ctx: { params: Promise<{ provider: string }> }) {
  const { provider } = await ctx.params;
  if (!(provider in PROVIDERS)) return Response.json({ detail: "unknown provider" }, { status: 404 });

  const url = new URL(req.url);
  const session = await getSession();
  if (!session) redirect(`/login?next=${encodeURIComponent(url.pathname + url.search)}`);

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

  const target = new URL(safePath(finished.return_to, "/settings"), publicOrigin(req.headers));
  for (const [k, v] of Object.entries(finished.query)) target.searchParams.set(k, v);
  redirect(target.pathname + target.search);
}
