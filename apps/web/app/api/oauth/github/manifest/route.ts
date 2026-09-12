import { redirect } from "next/navigation";
import { appFor, signState } from "@/lib/oauth";
import { getSession } from "@/lib/session";
import { setupStatus } from "@/lib/setup";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const session = await getSession();
  if (!session && (await setupStatus()).complete) redirect("/login");
  if (appFor("github")) return Response.json({ detail: "a GitHub app is already configured" }, { status: 409 });

  const org = url.searchParams.get("org")?.trim() || "";
  const returnTo = url.searchParams.get("return") || "/settings";
  const state = signState({ orgId: url.searchParams.get("orgId") || "", returnTo });
  const target = org ? `https://github.com/organizations/${encodeURIComponent(org)}/settings/apps/new` : "https://github.com/settings/apps/new";

  const manifest = {
    name: `Action Platform (${url.host})`.slice(0, 34),
    url: url.origin,
    redirect_url: `${url.origin}/api/oauth/github/manifest/callback`,
    callback_urls: [`${url.origin}/api/oauth/github/callback`],
    setup_url: `${url.origin}${returnTo}`,
    public: false,
    request_oauth_on_install: true,
    default_permissions: { administration: "write", contents: "write", workflows: "write", pull_requests: "write", metadata: "read" },
  };

  const html = `<!doctype html><meta charset="utf-8"><title>Creating the GitHub App…</title>
<body style="font:14px system-ui;background:#080808;color:#f5f5f5;display:grid;place-items:center;height:100vh;margin:0">
<form id="f" method="post" action="${target}?state=${encodeURIComponent(state)}">
<input type="hidden" name="manifest" value='${JSON.stringify(manifest).replace(/'/g, "&#39;")}'>
<noscript><button>Continue to GitHub</button></noscript>
</form>
<p>Taking you to GitHub…</p>
<script>document.getElementById("f").submit()</script></body>`;

  return new Response(html, { headers: { "content-type": "text/html; charset=utf-8" } });
}
