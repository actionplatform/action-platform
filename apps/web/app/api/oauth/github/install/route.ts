import { redirect } from "next/navigation";
import { ApiError } from "@/lib/api";
import { publicOrigin } from "@/lib/origin";
import { safePath } from "@/lib/safe-path";
import { getSession } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const session = await getSession();
  if (!session) redirect("/login?next=/settings");

  const back = safePath(url.searchParams.get("return"), "/connect/git");
  let target: string;
  try {
    target = (await v1.githubInstall(publicOrigin(req.headers), back)).url;
  } catch (e) {
    if (e instanceof ApiError && e.status === 409) redirect(`/api/oauth/github/manifest?${new URLSearchParams({ return: back })}`);
    return Response.json({ detail: (e as Error).message }, { status: 400 });
  }
  redirect(target);
}
