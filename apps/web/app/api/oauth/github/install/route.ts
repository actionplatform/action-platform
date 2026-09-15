import { redirect } from "next/navigation";
import { publicOrigin } from "@/lib/origin";
import { safePath } from "@/lib/safe-path";
import { getSession } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const session = await getSession();
  if (!session) redirect("/login?next=/settings");

  let target: string;
  try {
    target = (await v1.githubInstall(publicOrigin(req.headers), safePath(url.searchParams.get("return"), "/settings/hosts"))).url;
  } catch (e) {
    return Response.json({ detail: (e as Error).message }, { status: 400 });
  }
  redirect(target);
}
