"use server";

import { revalidatePath } from "next/cache";
import { writeConfig } from "@/lib/config";
import { type Provider, PROVIDERS } from "@/lib/oauth";
import { getSession } from "@/lib/session";
import { setupStatus } from "@/lib/setup";

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
