// Remote surface for the CLI and the MCP server: a bearer session (from
// `action-platform login`) or the browser cookie, then a pass-through to
// the Python API that runs next to this app. Path and query are forwarded
// as-is, so /api/v1/projects/<id>/release is the same contract as the
// Python side documents at /docs.
import { API_BASE } from "@/lib/api";
import { getAuth } from "@/lib/auth";

async function proxy(req: Request, path: string[]): Promise<Response> {
  const auth = await getAuth();
  const session = await auth.api.getSession({ headers: req.headers });
  if (!session) return Response.json({ detail: "unauthorized" }, { status: 401 });

  const url = new URL(req.url);
  const target = `${API_BASE}/api/${path.join("/")}${url.search}`;
  const body = req.method === "GET" || req.method === "HEAD" ? undefined : await req.text();

  const upstream = await fetch(target, {
    method: req.method,
    headers: { "content-type": req.headers.get("content-type") ?? "application/json" },
    body,
    cache: "no-store",
  });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
  });
}

type Ctx = { params: Promise<{ path: string[] }> };

export async function GET(req: Request, ctx: Ctx) { return proxy(req, (await ctx.params).path); }
export async function POST(req: Request, ctx: Ctx) { return proxy(req, (await ctx.params).path); }
export async function DELETE(req: Request, ctx: Ctx) { return proxy(req, (await ctx.params).path); }
