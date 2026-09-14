import { redirect } from "next/navigation";
import { publicOrigin } from "@/lib/origin";
import { safePath } from "@/lib/safe-path";
import { getSession } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const session = await getSession();
  if (!session) redirect(`/login?next=${encodeURIComponent(url.pathname + url.search)}`);

  let page: { target: string; manifest: Record<string, unknown> };
  try {
    page = await v1.githubManifest({ origin: publicOrigin(req.headers), host: url.host, return_to: safePath(url.searchParams.get("return"), "/settings"), github_org: url.searchParams.get("org")?.trim() || "" });
  } catch (e) {
    const status = e instanceof Error && "status" in e ? (e as { status: number }).status : 400;
    return Response.json({ detail: (e as Error).message }, { status });
  }

  const html = `<!doctype html><meta charset="utf-8"><title>Creating the GitHub App…</title>
<body style="font:14px system-ui;background:#080808;color:#f5f5f5;display:grid;place-items:center;height:100vh;margin:0">
<form id="f" method="post" action="${page.target}">
<input type="hidden" name="manifest" value='${JSON.stringify(page.manifest).replace(/'/g, "&#39;")}'>
<noscript><button>Continue to GitHub</button></noscript>
</form>
<p>Taking you to GitHub…</p>
<script>document.getElementById("f").submit()</script></body>`;

  return new Response(html, { headers: { "content-type": "text/html; charset=utf-8" } });
}
