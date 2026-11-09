import { redirect } from "next/navigation";
import { requestClient, setSessionCookie } from "@/lib/auth";
import { authApi } from "@/lib/auth-api";
import { loginWithError, takeVerifier } from "@/lib/google-sign-in";
import { publicOrigin } from "@/lib/origin";
import { safePath } from "@/lib/safe-path";

export async function GET(req: Request) {
  const params = new URL(req.url).searchParams;
  const verifier = await takeVerifier();
  if (params.get("error")) redirect(loginWithError("Google sign-in was cancelled"));
  const code = params.get("code");
  const state = params.get("state");
  if (!code || !state || !verifier) redirect(loginWithError("the Google sign-in expired, start again"));

  let next: string;
  try {
    const { ip, userAgent } = await requestClient();
    const signed = await authApi.googleCallback({ origin: publicOrigin(req.headers), code, state, verifier, ip_address: ip, user_agent: userAgent }, ip);
    await setSessionCookie(signed.session.cookie, signed.session.expires_at);
    next = safePath(signed.next, "/projects");
  } catch (e) {
    redirect(loginWithError((e as Error).message || "Google sign-in failed"));
  }
  redirect(next);
}
