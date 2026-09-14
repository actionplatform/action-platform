"use server";

import { failed } from "@/lib/result";
import { sessionCookie } from "@/lib/auth";
import { signUp } from "@/lib/auth-actions";
import { authApi } from "@/lib/auth-api";
import { setupStatus } from "@/lib/setup";
import { type HostKind } from "@/lib/source-host-kinds";
import { slugify } from "@/lib/utils";
import { DEFAULT_GIT_AUTHOR } from "@/lib/org-settings";
import { v1 } from "@/lib/v1";

type Result = { ok: true; note?: string } | { ok: false; error: string };

export async function checkApi(): Promise<Result> {
  const status = await setupStatus();
  if (status.error) return { ok: false, error: status.error };
  return { ok: true };
}

export async function createAdmin(input: { name: string; email: string; password: string }): Promise<Result> {
  const status = await setupStatus();
  if (!status.dbOk) return { ok: false, error: status.error ?? "the API is not ready" };
  if (status.hasUser) return { ok: false, error: "an account already exists — sign in instead" };

  const created = await signUp(input.name, input.email, input.password);
  return created.ok ? { ok: true } : created;
}

export async function createFirstOrganization(input: { name: string; slug: string; gitAuthorName?: string; gitAuthorEmail?: string }): Promise<{ ok: true; orgId: string } | { ok: false; error: string }> {
  const status = await setupStatus();
  if (!status.hasUser) return { ok: false, error: "create the admin account first" };
  if (status.hasOrg) return { ok: false, error: "an organization already exists" };

  const name = input.name.trim();
  const slug = slugify(input.slug || name);
  if (!name || !slug) return { ok: false, error: "name and slug are required" };

  try {
    const cookie = await sessionCookie();
    if (!cookie) return { ok: false, error: "sign in as the admin first" };
    const org = await authApi.createOrganization({ cookie }, { name, slug, git_author_name: input.gitAuthorName || DEFAULT_GIT_AUTHOR.name, git_author_email: input.gitAuthorEmail || DEFAULT_GIT_AUTHOR.email });
    return { ok: true, orgId: org.id };
  } catch (e) {
    return failed(e);
  }
}

export type HostInput = { kind: HostKind; name: string; baseUrl: string; username: string; token: string; defaultOwner: string };

export async function addSetupHost(_orgId: string, input: HostInput): Promise<Result> {
  const status = await setupStatus();
  if (!status.hasOrg) return { ok: false, error: "create the organization first" };

  try {
    await v1.addHost({ kind: input.kind, name: input.name, base_url: input.baseUrl, username: input.username, token: input.token, default_owner: input.defaultOwner });
    return { ok: true };
  } catch (e) {
    return failed(e);
  }
}
