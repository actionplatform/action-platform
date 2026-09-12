import { redirect } from "next/navigation";
import { writeConfig } from "@/lib/config";
import { verifyState } from "@/lib/oauth";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const state = verifyState(url.searchParams.get("state"));
  if (!state) return Response.json({ detail: "invalid or expired state" }, { status: 400 });

  const back = (query: Record<string, string>) => {
    const target = new URL(state.returnTo, url.origin);
    for (const [k, v] of Object.entries(query)) target.searchParams.set(k, v);
    redirect(target.pathname + target.search);
  };

  const code = url.searchParams.get("code");
  if (!code) return back({ oauth_error: "GitHub sent no code" });

  const res = await fetch(`https://api.github.com/app-manifests/${encodeURIComponent(code)}/conversions`, {
    method: "POST",
    headers: { accept: "application/vnd.github+json", "user-agent": "action-platform", "x-github-api-version": "2022-11-28" },
    cache: "no-store",
  });
  if (!res.ok) return back({ oauth_error: `GitHub app creation failed (${res.status})` });

  const app = (await res.json()) as { slug: string; client_id: string; client_secret: string; html_url: string };
  writeConfig({ oauth: { github: { clientId: app.client_id, clientSecret: app.client_secret, slug: app.slug } } });

  return back({ github_app: app.slug });
}
