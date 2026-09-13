"use server";

import { failed, type Result } from "@/lib/result";
import { revalidatePath } from "next/cache";
import { addMemberAccount, cancelInvitation, createInvitation, removeMember, requireManager, type Role, ROLES, setMemberRole } from "@/lib/orgs";
import { requireOrg } from "@/lib/session";
import { setGitAuthor } from "@/lib/org-settings";
import { addHost, HOST_KINDS, type HostKind, removeHost, setHostOwner, updateHostToken } from "@/lib/source-hosts";

export async function createHost(_prev: { error?: string } | null, formData: FormData): Promise<{ error?: string } | null> {
  const { session, org } = await requireOrg();
  try {
    await requireManager(session.user.id, org.id);
  } catch (e) {
    return { error: (e as Error).message };
  }
  const kind = String(formData.get("kind") ?? "") as HostKind;
  if (!HOST_KINDS.some((k) => k.id === kind)) return { error: "unknown host kind" };
  const token = String(formData.get("token") ?? "").trim();
  if (!token) return { error: "token is required" };

  try {
    await addHost(org.id, {
      kind,
      name: String(formData.get("name") ?? "").trim() || HOST_KINDS.find((k) => k.id === kind)!.label,
      baseUrl: String(formData.get("baseUrl") ?? "").trim(),
      username: String(formData.get("username") ?? "").trim(),
      token,
      defaultOwner: String(formData.get("defaultOwner") ?? "").trim(),
    });
  } catch (e) {
    return { error: (e as Error).message };
  }

  revalidatePath("/settings");
  return { error: undefined };
}

export async function deleteHost(id: string) {
  const { session, org } = await requireOrg();
  await requireManager(session.user.id, org.id);
  await removeHost(org.id, id);
  revalidatePath("/settings");
}

export async function rotateHostToken(id: string, token: string): Promise<{ error?: string } | null> {
  const { session, org } = await requireOrg();
  try {
    await requireManager(session.user.id, org.id);
  } catch (e) {
    return { error: (e as Error).message };
  }
  if (!token.trim()) return { error: "token is required" };
  await updateHostToken(org.id, id, token.trim());
  revalidatePath("/settings");
  return null;
}


export async function inviteMember(email: string, role: Role): Promise<Result<{ id: string }>> {
  const { session, org } = await requireOrg();
  try {
    await requireManager(session.user.id, org.id);
    if (!ROLES.includes(role)) throw new Error("unknown role");
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) throw new Error("enter a valid email");
    const invitation = await createInvitation(org.id, session.user.id, email, role);
    revalidatePath("/settings");
    return { ok: true, data: { id: invitation.id } };
  } catch (e) {
    return failed(e);
  }
}

export async function revokeInvitation(id: string): Promise<Result> {
  const { session, org } = await requireOrg();
  try {
    await requireManager(session.user.id, org.id);
    await cancelInvitation(org.id, id);
    revalidatePath("/settings");
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function changeRole(memberId: string, role: Role): Promise<Result> {
  const { session, org } = await requireOrg();
  try {
    await requireManager(session.user.id, org.id);
    if (!ROLES.includes(role)) throw new Error("unknown role");
    await setMemberRole(org.id, memberId, role);
    revalidatePath("/settings");
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function kickMember(memberId: string): Promise<Result> {
  const { session, org } = await requireOrg();
  try {
    await requireManager(session.user.id, org.id);
    await removeMember(org.id, memberId);
    revalidatePath("/settings");
    revalidatePath("/teams");
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function addMember(input: { name: string; email: string; password: string; role: Role }): Promise<Result<{ existed: boolean }>> {
  const { session, org } = await requireOrg();
  try {
    await requireManager(session.user.id, org.id);
    if (!ROLES.includes(input.role)) throw new Error("unknown role");
    const r = await addMemberAccount(org.id, input);
    revalidatePath("/settings");
    revalidatePath("/teams");
    return { ok: true, data: { existed: r.existed } };
  } catch (e) {
    return failed(e);
  }
}

export async function changeHostOwner(id: string, owner: string): Promise<Result> {
  const { session, org } = await requireOrg();
  try {
    await requireManager(session.user.id, org.id);
    await setHostOwner(org.id, id, owner);
    revalidatePath("/settings");
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function saveGitAuthor(author: { name: string; email: string }): Promise<Result<{ name: string; email: string }>> {
  const { session, org } = await requireOrg();
  try {
    await requireManager(session.user.id, org.id);
    const data = await setGitAuthor(org.id, author);
    revalidatePath("/settings");
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}
