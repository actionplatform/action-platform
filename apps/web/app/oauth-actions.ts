"use server";

import { revalidatePath } from "next/cache";
import { clearOAuthApp, writeConfig } from "@/lib/config";
import { type Provider, PROVIDERS } from "@/lib/oauth";
import { activeOrg } from "@/lib/orgs";
import { getSession } from "@/lib/session";
import { setupStatus } from "@/lib/setup";
import { removeOAuthHost } from "@/lib/source-hosts";

export async function saveOAuthApp(input: { provider: Provider; clientId: string; clientSecret: string; baseUrl: string }): Promise<{ ok: true } | { ok: false; error: string }> {
  if (!(input.provider in PROVIDERS)) return { ok: false, error: "unknown provider" };

  const session = await getSession();
  if (!session && (await setupStatus()).complete) return { ok: false, error: "sign in first" };

  const clientId = input.clientId.trim();
  const clientSecret = input.clientSecret.trim();
  if (!clientId || !clientSecret) return { ok: false, error: "client id and secret are required" };

  writeConfig({ oauth: { [input.provider]: { clientId, clientSecret, baseUrl: input.baseUrl.trim() || undefined } } });
  revalidatePath("/settings");
  return { ok: true };
}

export async function removeOAuthApp(provider: Provider): Promise<{ ok: true } | { ok: false; error: string }> {
  if (!(provider in PROVIDERS)) return { ok: false, error: "unknown provider" };
  const session = await getSession();
  if (!session && (await setupStatus()).complete) return { ok: false, error: "sign in first" };
  clearOAuthApp(provider);
  revalidatePath("/settings");
  return { ok: true };
}

export async function disconnectHost(provider: Provider, login: string): Promise<{ ok: true } | { ok: false; error: string }> {
  const session = await getSession();
  if (!session) return { ok: false, error: "sign in first" };
  const org = await activeOrg(session);
  if (!org) return { ok: false, error: "no organization" };
  await removeOAuthHost(org.id, provider, login);
  revalidatePath("/settings");
  return { ok: true };
}
