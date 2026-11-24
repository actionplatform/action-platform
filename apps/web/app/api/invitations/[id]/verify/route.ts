import { redirect } from "next/navigation";
import { failed } from "@/lib/result";
import { publicOrigin } from "@/lib/origin";
import { verifyInvitationStart } from "@/lib/orgs";
import { getSession } from "@/lib/session";

export async function GET(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const back = `/invite/${encodeURIComponent(id)}`;
  if (!(await getSession())) redirect(`/login?next=${encodeURIComponent(back)}`);

  let target: string;
  try {
    target = await verifyInvitationStart(id, publicOrigin(req.headers));
  } catch (e) {
    redirect(`${back}?error=${encodeURIComponent(failed(e).error)}`);
  }
  redirect(target);
}
