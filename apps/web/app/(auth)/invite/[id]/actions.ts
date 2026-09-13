"use server";

import { getSetupAuth } from "@/lib/auth";
import { acceptInvitation, invitationById } from "@/lib/orgs";
import { getSession } from "@/lib/session";

type Result = { ok: true } | { ok: false; error: string };

export async function acceptInvite(id: string): Promise<Result> {
  const session = await getSession();
  if (!session) return { ok: false, error: "sign in first" };
  try {
    await acceptInvitation(id, session.user.id, session.user.email);
    return { ok: true };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
}

export async function joinWithNewAccount(id: string, name: string, password: string): Promise<Result> {
  const invitation = await invitationById(id);
  if (!invitation || invitation.status !== "pending" || invitation.expired) return { ok: false, error: "invitation is no longer valid" };
  if (!name.trim()) return { ok: false, error: "name is required" };
  if (password.length < 8) return { ok: false, error: "password needs at least 8 characters" };
  try {
    await (await getSetupAuth()).api.signUpEmail({ body: { name: name.trim(), email: invitation.email, password } });
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
  const session = await getSession();
  if (!session) return { ok: false, error: "account created; sign in to join" };
  return acceptInvite(id);
}
