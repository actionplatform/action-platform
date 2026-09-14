import { API_BASE, apiHeaders } from "./api";
import { API_TIMEOUT_MS } from "./timeouts";

export async function forwardAuth(req: Request, path: string): Promise<Response> {
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || req.headers.get("x-real-ip") || "";
  const body = await req.text();
  const upstream = await fetch(`${API_BASE}/api/auth/${path}`, {
    method: "POST",
    headers: { ...apiHeaders, "content-type": "application/json", ...(ip ? { "x-forwarded-for": ip } : {}) },
    body,
    cache: "no-store",
    signal: AbortSignal.timeout(API_TIMEOUT_MS),
  });
  return new Response(await upstream.text(), { status: upstream.status, headers: { "content-type": "application/json", "cache-control": "no-store" } });
}
