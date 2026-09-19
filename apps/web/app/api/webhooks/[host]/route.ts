import { API_BASE } from "@/lib/api";

const RETURNED = ["content-type", "cache-control", "retry-after", "www-authenticate"];
const FORWARDED = ["content-type", "x-github-event", "x-github-delivery", "x-hub-signature-256", "x-hub-signature", "x-gitlab-event", "x-gitlab-token", "x-event-key", "x-request-uuid", "user-agent"];

export async function POST(req: Request, ctx: { params: Promise<{ host: string }> }) {
  const { host } = await ctx.params;
  if (!/^[A-Za-z0-9_-]{1,64}$/.test(host)) return Response.json({ detail: "unknown host" }, { status: 404 });

  const body = await req.arrayBuffer();
  const headers = new Headers();
  for (const name of FORWARDED) {
    const value = req.headers.get(name);
    if (value) headers.set(name, value);
  }

  const upstream = await fetch(`${API_BASE}/api/v1/webhooks/${host}`, { method: "POST", headers, body, signal: AbortSignal.timeout(15_000) }).catch(() => null);
  if (!upstream) return Response.json({ detail: "the platform did not answer" }, { status: 502 });

  const headersOut = new Headers();
  for (const name of RETURNED) {
    const value = upstream.headers.get(name);
    if (value) headersOut.set(name, value);
  }
  if (!headersOut.has("content-type")) headersOut.set("content-type", "application/json");

  return new Response(await upstream.text(), { status: upstream.status, headers: headersOut });
}
