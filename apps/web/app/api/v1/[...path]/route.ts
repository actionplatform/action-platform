import { API_BASE } from "@/lib/api";
import { getAuth } from "@/lib/auth";
import { activeOrg, roleOf } from "@/lib/orgs";
import { can, type Permission } from "@/lib/permissions";
import { appByRegistryId, registryIdsOf } from "@/lib/projects";
import { syncPullRequests } from "@/lib/pull-requests";
import { syncReleases } from "@/lib/releases";
import { credentialsFor } from "@/lib/source-hosts";

type Rule = { method: string; pattern: RegExp; permission: Permission | null; credentials?: boolean; imports?: boolean };

const RULES: Rule[] = [
  { method: "GET", pattern: /^(version|matrix|gitflow\/rules)$/, permission: null },
  { method: "GET", pattern: /^apps$/, permission: null },
  { method: "POST", pattern: /^apps$/, permission: "project.manage" },
  { method: "POST", pattern: /^apps\/init$/, permission: "project.manage", credentials: true },
  { method: "GET", pattern: /^apps\/[^/]+(\/.*)?$/, permission: null },
  { method: "DELETE", pattern: /^apps\/[^/]+$/, permission: "project.manage" },
  { method: "POST", pattern: /^apps\/[^/]+\/sync$/, permission: "app.sync", credentials: true, imports: true },
  { method: "POST", pattern: /^apps\/[^/]+\/release$/, permission: "app.release", credentials: true, imports: true },
  { method: "POST", pattern: /^apps\/[^/]+\/deploy$/, permission: "app.release" },
  { method: "POST", pattern: /^apps\/[^/]+\/(push|branches|checkout|pull-request)$/, permission: "app.flow", credentials: true, imports: true },
  { method: "PUT", pattern: /^apps\/[^/]+\/manifest$/, permission: "app.configure" },
  { method: "POST", pattern: /^apps\/[^/]+\/(cloud|services)$/, permission: "app.configure" },
  { method: "POST", pattern: /^apps\/[^/]+\/commit$/, permission: "app.configure", credentials: true, imports: true },
];

function ruleFor(method: string, path: string): Rule | null {
  return RULES.find((r) => r.method === method && r.pattern.test(path)) ?? null;
}

async function proxy(req: Request, segments: string[]): Promise<Response> {
  const auth = await getAuth();
  const session = await auth.api.getSession({ headers: req.headers });
  if (!session) return Response.json({ detail: "unauthorized" }, { status: 401 });

  const org = await activeOrg(session);
  if (!org) return Response.json({ detail: "no organization" }, { status: 403 });

  const path = segments.join("/");
  const rule = ruleFor(req.method, path);
  if (!rule) return Response.json({ detail: `${req.method} /api/v1/${path} is not exposed` }, { status: 404 });

  const role = await roleOf(session.user.id, org.id);
  if (rule.permission && !can(role, rule.permission)) return Response.json({ detail: `your role (${role ?? "none"}) lacks ${rule.permission}` }, { status: 403 });

  const registryId = path.startsWith("apps/") ? segments[1] : null;
  const app = registryId && registryId !== "init" ? await appByRegistryId(registryId) : null;
  if (registryId && registryId !== "init" && (!app || app.organizationId !== org.id)) return Response.json({ detail: "app not found" }, { status: 404 });

  const url = new URL(req.url);
  const target = `${API_BASE}/api/${path}${url.search}`;
  let body = req.method === "GET" || req.method === "HEAD" ? undefined : await req.text();

  if (rule.credentials && body !== undefined && app?.sourceHostId) {
    const parsed = body ? (JSON.parse(body) as Record<string, unknown>) : {};
    if (!parsed.credentials) parsed.credentials = await credentialsFor(org.id, app.sourceHostId);
    body = JSON.stringify(parsed);
  }

  const upstream = await fetch(target, {
    method: req.method,
    headers: { "content-type": req.headers.get("content-type") ?? "application/json" },
    body,
    cache: "no-store",
  });

  if (req.method === "GET" && path === "apps") {
    const allowed = await registryIdsOf(org.id);
    const rows = (await upstream.json()) as { id: string }[];
    return Response.json(rows.filter((r) => allowed.has(r.id)), { status: upstream.status });
  }

  if (rule.imports && upstream.ok && app) {
    const detail = await fetch(`${API_BASE}/api/apps/${app.registryId}`, { cache: "no-store" }).then((r) => (r.ok ? (r.json() as Promise<{ url: string; source_host: { repo: string | null } }>) : null)).catch(() => null);
    const repo = detail?.source_host.repo ?? detail?.url.match(/[:/]([^/:]+\/[^/]+?)(?:\.git)?$/)?.[1] ?? null;
    await Promise.allSettled([syncReleases(org.id, app.id, app.sourceHostId, repo), syncPullRequests(org.id, app.id, app.sourceHostId, repo)]);
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
  });
}

type Ctx = { params: Promise<{ path: string[] }> };

export async function GET(req: Request, ctx: Ctx) { return proxy(req, (await ctx.params).path); }
export async function POST(req: Request, ctx: Ctx) { return proxy(req, (await ctx.params).path); }
export async function PUT(req: Request, ctx: Ctx) { return proxy(req, (await ctx.params).path); }
export async function DELETE(req: Request, ctx: Ctx) { return proxy(req, (await ctx.params).path); }
