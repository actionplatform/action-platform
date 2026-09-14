import { hkdfSync } from "node:crypto";
import { readConfig } from "./config";

export type Purpose = "api-token" | "oauth-state" | "source-host";

export function subkey(purpose: Purpose, length = 32): Buffer {
  const secret = readConfig().authSecret;
  if (!secret) throw new Error("auth secret is not configured");
  return Buffer.from(hkdfSync("sha256", secret, "action-platform", purpose, length));
}
