import { PROVIDER_TIMEOUT_MS } from "@/lib/timeouts";
import { redirect } from "next/navigation";
import { writeConfig } from "@/lib/config";
import { verifyState } from "@/lib/oauth";
import { publicOrigin } from "@/lib/origin";
import { getSession } from "@/lib/session";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const session = await getSession();
  const state = verifyState(url.searchParams.get("state"), session?.user.id ?? null);
  if (!state) return Response.json({ detail: "invalid or expired state" }, { status: 400 });

  const back = (query: Record<string, string>) => {
    const target = new URL(state.returnTo, publicOrigin(req.headers));
    for (const [k, v] of Object.entries(query)) target.searchParams.set(k, v);
    redirect(target.pathname + target.search);
  };

  const code = url.searchParams.get("code");
  if (!code) return back({ oauth_error: "GitHub sent no code" });

  const res = await fetch(`https://api.github.com/app-manifests/${encodeURIComponent(code)}/conversions`, {
    method: "POST",
    headers: { accept: "application/vnd.github+json", "user-agent": "action-platform", "x-github-api-version": "2022-11-28" },
    cache: "no-store", signal: AbortSignal.timeout(PROVIDER_TIMEOUT_MS),
  });
  if (!res.ok) return back({ oauth_error: `GitHub app creation failed (${res.status})` });

  const app = (await res.json()) as { slug: string; client_id: string; client_secret: string; html_url: string };
  writeConfig({ oauth: { github: { clientId: app.client_id, clientSecret: app.client_secret, slug: app.slug } } });

  return back({ github_app: app.slug });
}
