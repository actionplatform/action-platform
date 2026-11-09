import { cookies } from "next/headers";
import { GOOGLE_PATH } from "./google-sign-in-path";

export { loginWithError } from "./google-sign-in-path";

export const VERIFIER_COOKIE = "ap.google_verifier";

function secure(): boolean {
  return (process.env.PUBLIC_URL ?? process.env.BETTER_AUTH_URL ?? "").startsWith("https://");
}

export async function keepVerifier(verifier: string): Promise<void> {
  const jar = await cookies();
  jar.set(VERIFIER_COOKIE, verifier, { httpOnly: true, sameSite: "lax", secure: secure(), path: GOOGLE_PATH, maxAge: 600 });
}

export async function takeVerifier(): Promise<string | null> {
  const jar = await cookies();
  const verifier = jar.get(VERIFIER_COOKIE)?.value ?? null;
  jar.delete({ name: VERIFIER_COOKIE, path: GOOGLE_PATH });
  return verifier;
}
