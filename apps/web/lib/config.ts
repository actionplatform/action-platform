// Runtime configuration written by the setup wizard. Environment variables
// win when present, so a hosted deploy can skip the wizard entirely.
import { randomBytes } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

export type OAuthApp = { clientId: string; clientSecret: string; baseUrl?: string };

export type AppConfig = {
  databaseUrl?: string;
  authSecret?: string;
  // OAuth apps registered at each provider so members can "Connect with…"
  oauth?: Partial<Record<"github" | "gitlab" | "bitbucket", OAuthApp>>;
};

const FILE = resolve(process.env.AP_WEB_CONFIG ?? "config/app.json");

export function readConfig(): AppConfig {
  const file: AppConfig = existsSync(FILE) ? JSON.parse(readFileSync(FILE, "utf8")) : {};

  return {
    databaseUrl: process.env.DATABASE_URL ?? file.databaseUrl,
    authSecret: process.env.BETTER_AUTH_SECRET ?? file.authSecret,
    oauth: {
      ...(file.oauth ?? {}),
      ...envOAuth("github", "GITHUB"),
      ...envOAuth("gitlab", "GITLAB"),
      ...envOAuth("bitbucket", "BITBUCKET"),
    },
  };
}

function envOAuth(key: "github" | "gitlab" | "bitbucket", prefix: string): Partial<Record<typeof key, OAuthApp>> {
  const id = process.env[`${prefix}_CLIENT_ID`];
  const secret = process.env[`${prefix}_CLIENT_SECRET`];
  if (!id || !secret) return {};
  return { [key]: { clientId: id, clientSecret: secret, baseUrl: process.env[`${prefix}_BASE_URL`] } } as Partial<Record<typeof key, OAuthApp>>;
}

export function writeConfig(patch: AppConfig): AppConfig {
  const current: AppConfig = existsSync(FILE) ? JSON.parse(readFileSync(FILE, "utf8")) : {};
  const next = { ...current, ...patch, oauth: { ...(current.oauth ?? {}), ...(patch.oauth ?? {}) } };

  if (!next.authSecret) next.authSecret = randomBytes(32).toString("hex");

  mkdirSync(dirname(FILE), { recursive: true });
  writeFileSync(FILE, JSON.stringify(next, null, 2) + "\n", { mode: 0o600 });

  return next;
}
