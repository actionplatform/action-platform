import { redirect } from "next/navigation";
import { requestClient } from "@/lib/auth";
import { authApi } from "@/lib/auth-api";
import { keepVerifier, loginWithError } from "@/lib/google-sign-in";
import { publicOrigin } from "@/lib/origin";
import { safePath } from "@/lib/safe-path";

export async function GET(req: Request) {
  const next = safePath(new URL(req.url).searchParams.get("next"), "/projects");
  let url: string;
  try {
    const { ip } = await requestClient();
    const begun = await authApi.googleStart({ origin: publicOrigin(req.headers), next }, ip);
    await keepVerifier(begun.verifier);
    url = begun.url;
  } catch (e) {
    redirect(loginWithError((e as Error).message || "Google sign-in is not available"));
  }
  redirect(url);
}
