"use server";

import { failed } from "@/lib/result";
import { signUp } from "@/lib/auth-actions";
import { acceptInvitation, invitationById } from "@/lib/orgs";
import { getSession } from "@/lib/session";

type Result = { ok: true } | { ok: false; error: string };

export async function acceptInvite(id: string): Promise<Result> {
  const session = await getSession();
  if (!session) return { ok: false, error: "sign in first" };
  try {
    await acceptInvitation(id);
    return { ok: true };
  } catch (e) {
    return failed(e);
  }
}

export async function joinWithNewAccount(id: string, name: string, password: string): Promise<Result> {
  const invitation = await invitationById(id);
  if (!invitation || invitation.status !== "pending" || invitation.expired) return { ok: false, error: "invitation is no longer valid" };
  if (!name.trim()) return { ok: false, error: "name is required" };
  if (password.length < 8) return { ok: false, error: "password needs at least 8 characters" };
  const created = await signUp(name.trim(), invitation.email, password, id);
  if (!created.ok) return created;
  const session = await getSession();
  if (!session) return { ok: false, error: "account created; sign in to join" };
  return acceptInvite(id);
}
