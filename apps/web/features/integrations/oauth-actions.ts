"use server";

import { revalidatePath } from "next/cache";
import { type Provider, PROVIDERS } from "@/lib/oauth";
import { requireSession } from "@/lib/session";
import { v1 } from "@/lib/v1";

type Outcome = { ok: true } | { ok: false; error: string };

export async function saveOAuthApp(input: { provider: Provider; clientId: string; clientSecret: string; baseUrl: string }): Promise<Outcome> {
  if (!(input.provider in PROVIDERS)) return { ok: false, error: "unknown provider" };
  await requireSession();
  try {
    await v1.saveOAuthApp(input.provider, { client_id: input.clientId, client_secret: input.clientSecret, base_url: input.baseUrl });
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
  revalidatePath("/", "layout");
  return { ok: true };
}

export async function removeOAuthApp(provider: Provider): Promise<Outcome> {
  if (!(provider in PROVIDERS)) return { ok: false, error: "unknown provider" };
  await requireSession();
  try {
    await v1.clearOAuthApp(provider);
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
  revalidatePath("/", "layout");
  return { ok: true };
}

export async function disconnectHost(provider: Provider, login: string): Promise<Outcome> {
  await requireSession();
  try {
    await v1.disconnectOAuthHost(provider, login);
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
  revalidatePath("/", "layout");
  return { ok: true };
}
