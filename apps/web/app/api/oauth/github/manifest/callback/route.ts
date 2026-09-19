import { redirect } from "next/navigation";
import { publicOrigin } from "@/lib/origin";
import { safePath } from "@/lib/safe-path";
import { getSession } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const session = await getSession();
  if (!session) redirect(`/login?next=${encodeURIComponent(url.pathname + url.search)}`);

  let finished: { return_to: string; query: Record<string, string> };
  try {
    finished = await v1.githubManifestCallback({ code: url.searchParams.get("code"), state: url.searchParams.get("state") });
  } catch (e) {
    return Response.json({ detail: (e as Error).message }, { status: 400 });
  }

  const target = new URL(safePath(finished.return_to, "/settings"), publicOrigin(req.headers));
  for (const [k, v] of Object.entries(finished.query)) target.searchParams.set(k, v);
  redirect(target.pathname + target.search);
}
