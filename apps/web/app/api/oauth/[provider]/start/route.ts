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
  const returnTo = safePath(url.searchParams.get("return"), "/integrations/hosts");
  const session = await getSession();
  if (!session) redirect(`/login?next=${encodeURIComponent(url.pathname + url.search)}`);

  let target: string;
  try {
    target = (await v1.oauthStart(provider as Provider, publicOrigin(req.headers), returnTo)).url;
  } catch (e) {
    return Response.json({ detail: (e as Error).message }, { status: 400 });
  }
  redirect(target);
}
