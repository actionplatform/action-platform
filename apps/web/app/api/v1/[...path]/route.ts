import { API_BASE, apiHeaders } from "@/lib/api";
import { getAuth } from "@/lib/auth";
import { activeOrg, roleOf } from "@/lib/orgs";
import { can, type Permission } from "@/lib/permissions";
import { appByRegistryId, registryIdsOf } from "@/lib/projects";
import { syncPullRequests } from "@/lib/pull-requests";
import { syncReleases } from "@/lib/releases";
import { credentialsFor, hostsOf } from "@/lib/source-hosts";
import { sourceSpecByName, sourceSpecsOf } from "@/lib/template-sources";
import { gitAuthorOf } from "@/lib/org-settings";

type Rule = { method: string; pattern: RegExp; permission: Permission | null; credentials?: boolean; imports?: boolean };

const RULES: Rule[] = [
  { method: "GET", pattern: /^(version|matrix|gitflow\/rules)$/, permission: null },
  { method: "GET", pattern: /^apps$/, permission: null },
  { method: "POST", pattern: /^apps$/, permission: "project.manage", credentials: true },
  { method: "POST", pattern: /^apps\/init$/, permission: "project.manage", credentials: true },
  { method: "GET", pattern: /^apps\/[^/]+(\/.*)?$/, permission: null },
  { method: "DELETE", pattern: /^apps\/[^/]+$/, permission: "project.manage" },
  { method: "POST", pattern: /^apps\/[^/]+\/sync$/, permission: "app.sync", credentials: true, imports: true },
  { method: "POST", pattern: /^apps\/[^/]+\/release$/, permission: "app.release", credentials: true, imports: true },
  { method: "POST", pattern: /^apps\/[^/]+\/deploy$/, permission: "app.release" },
  { method: "POST", pattern: /^apps\/[^/]+\/(push|branches|checkout|pull-request)$/, permission: "app.flow", credentials: true, imports: true },
  { method: "PUT", pattern: /^apps\/[^/]+\/manifest$/, permission: "app.configure" },
  { method: "POST", pattern: /^apps\/[^/]+\/(cloud|services|install|discard)$/, permission: "app.configure" },
  { method: "POST", pattern: /^apps\/[^/]+\/commit$/, permission: "app.configure", credentials: true, imports: true },
];

async function hostIdForUrl(orgId: string, url: string): Promise<string | null> {
  const kind = url.includes("github.com") ? "github" : url.includes("gitlab") ? "gitlab" : url.includes("bitbucket.org") ? "bitbucket" : null;
  if (!kind) return null;
  return (await hostsOf(orgId)).find((h) => h.kind === kind)?.id ?? null;
}

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
  let method = req.method;
  let body = req.method === "GET" || req.method === "HEAD" ? undefined : await req.text();

  if (req.method === "GET" && path === "matrix") {
    method = "POST";
    body = JSON.stringify({ sources: await sourceSpecsOf(org.id) });
  }

  if (body !== undefined && /^apps\/(init|[^/]+\/(cloud|services))$/.test(path)) {
    const parsed = body ? (JSON.parse(body) as Record<string, unknown>) : {};
    if (typeof parsed.source === "string") parsed.source = await sourceSpecByName(org.id, parsed.source);
    body = JSON.stringify(parsed);
  }

  if (rule.credentials && body !== undefined) {
    const parsed = body ? (JSON.parse(body) as Record<string, unknown>) : {};
    const hostId = app?.sourceHostId ?? (typeof parsed.url === "string" ? await hostIdForUrl(org.id, parsed.url) : null);
    if (!parsed.credentials) {
      const creds = hostId ? await credentialsFor(org.id, hostId) : null;
      const identity = await gitAuthorOf(org.id);
      parsed.credentials = { ...(creds ?? {}), author_name: identity.name, author_email: identity.email };
    }
    body = JSON.stringify(parsed);
  }

  const upstream = await fetch(target, {
    method,
    headers: { "content-type": req.headers.get("content-type") ?? "application/json", ...apiHeaders },
    body,
    cache: "no-store",
  });

  if (req.method === "GET" && path === "apps") {
    const allowed = await registryIdsOf(org.id);
    const rows = (await upstream.json()) as { id: string }[];
    return Response.json(rows.filter((r) => allowed.has(r.id)), { status: upstream.status });
  }

  if (rule.imports && upstream.ok && app) {
    const detail = await fetch(`${API_BASE}/api/apps/${app.registryId}`, { cache: "no-store", headers: apiHeaders }).then((r) => (r.ok ? (r.json() as Promise<{ url: string; source_host: { repo: string | null } }>) : null)).catch(() => null);
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
