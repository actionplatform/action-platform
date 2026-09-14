import { API_TIMEOUT_MS, PROVIDER_TIMEOUT_MS } from "@/lib/timeouts";
import { API_BASE, apiHeaders } from "@/lib/api";
import { type Caller, authenticate } from "@/lib/api-auth";
import { membersOf, roleOf, setMemberRole } from "@/lib/orgs";
import { can, isRole, PERMISSIONS, type Permission, type Role, ROLE_INFO, ROLES, type Scope, scopeAllows } from "@/lib/permissions";
import type { Org } from "@/lib/types";
import { membersDirectory, organizationsOf, projectsDirectory, teamsDirectory } from "@/lib/directory";
import { appById, appByRegistryId, createProject, projectById, registryIdsOf } from "@/lib/projects";
import { addTeamMember, assignProjectTeam, createTeam } from "@/lib/teams";
import { syncPullRequests } from "@/lib/pull-requests";
import { syncReleases } from "@/lib/releases";
import { credentialsFor, hostsOf } from "@/lib/source-hosts";
import { sourceSpecByName, sourceSpecsOf } from "@/lib/template-sources";
import { gitAuthorOf } from "@/lib/org-settings";
import { formatGrant, parseGrant } from "@/lib/api-tokens";
import { authApi, isAuthError } from "@/lib/auth-api";

type Rule = { method: string; pattern: RegExp; permission: Permission | null; credentials?: boolean; imports?: boolean };

const RULES: Rule[] = [
  { method: "GET", pattern: /^(version|matrix|gitflow\/rules)$/, permission: null },
  { method: "GET", pattern: /^apps$/, permission: null },
  { method: "POST", pattern: /^apps$/, permission: "project.manage", credentials: true },
  { method: "POST", pattern: /^apps\/init$/, permission: "project.manage", credentials: true },
  { method: "GET", pattern: /^apps\/[^/]+$/, permission: null },
  { method: "GET", pattern: /^apps\/[^/]+\/(gitflow|commits|branches|tags|releases|changes|manifest|diagnose|pull-request)$/, permission: null },
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
  const caller = await authenticate(req);
  if (!caller) return Response.json({ detail: "unauthorized" }, { status: 401 });
  if (!caller.org && !caller.allOrgs) return Response.json({ detail: "no organization" }, { status: 403 });

  const path = segments.join("/");
  if (path === "me") return Response.json(await me(caller));
  if (path === "tokens") return issue(req, caller);
  if (path === "organizations") return Response.json(await organizationsOf(caller.user.id));
  if (DIRECTORY.has(path) && req.method === "GET") return directory(path, req, caller);
  if (DIRECTORY.has(path) && req.method === "POST") return manage(path, req, caller);

  const rule = ruleFor(req.method, path);
  if (!rule) return Response.json({ detail: `${req.method} /api/v1/${path} is not exposed` }, { status: 404 });

  const registryId = path.startsWith("apps/") ? segments[1] : null;
  const app = registryId && registryId !== "init" ? await appByRegistryId(registryId) : null;
  const org = app ? caller.orgs.find((o) => o.id === app.organizationId) ?? null : requestedOrg(req, caller) ?? (req.method === "GET" && path === "apps" ? null : caller.org);
  if (registryId && registryId !== "init" && (!app || !org || (caller.org && caller.org.id !== org.id))) return Response.json({ detail: "app not found" }, { status: 404 });
  if (!org && !(req.method === "GET" && path === "apps")) return Response.json({ detail: "this token spans every organization: send X-Organization: <id or slug>" }, { status: 400 });

  const role = org ? await roleOf(caller.user.id, org.id) : null;
  if (org && rule.permission && !can(role, rule.permission)) return Response.json({ detail: `your role (${role ?? "none"}) lacks ${rule.permission}` }, { status: 403 });
  if (caller.scope && !scopeAllows(caller.scope, rule.permission)) return Response.json({ detail: `the token's scope (${caller.scope.join(" ")}) does not allow ${rule.permission ?? "read"}` }, { status: 403 });
  if (app && !withinReach(caller, app)) return Response.json({ detail: "app not found" }, { status: 404 });
  if (!app && req.method === "POST" && /^apps(\/init)?$/.test(path) && (caller.projectId || caller.appId)) return Response.json({ detail: "this token is limited to one project; it cannot add apps" }, { status: 403 });

  const url = new URL(req.url);
  const target = `${API_BASE}/api/${path}${url.search}`;
  let method = req.method;
  let body = req.method === "GET" || req.method === "HEAD" ? undefined : await req.text();

  if (req.method === "GET" && path === "matrix") {
    method = "POST";
    body = JSON.stringify({ sources: await sourceSpecsOf(org!.id) });
  }

  if (body !== undefined && /^apps\/(init|[^/]+\/(cloud|services))$/.test(path)) {
    const parsed = body ? (JSON.parse(body) as Record<string, unknown>) : {};
    if (typeof parsed.source === "string") parsed.source = await sourceSpecByName(org!.id, parsed.source);
    body = JSON.stringify(parsed);
  }

  if (rule.credentials && body !== undefined) {
    const parsed = body ? (JSON.parse(body) as Record<string, unknown>) : {};
    const hostId = app?.sourceHostId ?? (typeof parsed.url === "string" ? await hostIdForUrl(org!.id, parsed.url) : null);
    if (!parsed.credentials) {
      const creds = hostId ? await credentialsFor(org!.id, hostId) : null;
      const identity = await gitAuthorOf(org!.id);
      parsed.credentials = { ...(creds ?? {}), author_name: identity.name, author_email: identity.email };
    }
    body = JSON.stringify(parsed);
  }

  const upstream = await fetch(target, {
    method,
    headers: { "content-type": req.headers.get("content-type") ?? "application/json", ...apiHeaders },
    body,
    cache: "no-store",
    signal: AbortSignal.timeout(API_TIMEOUT_MS),
  });

  if (req.method === "GET" && path === "apps") {
    const allowed = new Set<string>();
    for (const o of org ? [org] : caller.orgs) for (const id of await registryIdsOf(o.id, caller.projectId, caller.appId)) allowed.add(id);
    const rows = (await upstream.json()) as { id: string }[];
    return Response.json(rows.filter((r) => allowed.has(r.id)), { status: upstream.status });
  }

  if (rule.imports && upstream.ok && app && org) {
    const detail = await fetch(`${API_BASE}/api/apps/${app.registryId}`, { cache: "no-store", signal: AbortSignal.timeout(PROVIDER_TIMEOUT_MS), headers: apiHeaders }).then((r) => (r.ok ? (r.json() as Promise<{ url: string; source_host: { repo: string | null } }>) : null)).catch(() => null);
    const repo = detail?.source_host.repo ?? detail?.url.match(/[:/]([^/:]+\/[^/]+?)(?:\.git)?$/)?.[1] ?? null;
    await Promise.allSettled([syncReleases(org.id, app.id, app.sourceHostId, repo), syncPullRequests(org.id, app.id, app.sourceHostId, repo)]);
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
  });
}

function requestedOrg(req: Request, caller: Caller): Org | null {
  if (caller.org) return caller.org;
  const wanted = (req.headers.get("x-organization") ?? new URL(req.url).searchParams.get("organization") ?? "").trim();
  if (!wanted) return null;
  return caller.orgs.find((o) => o.id === wanted || o.slug === wanted) ?? null;
}

async function me(caller: Caller) {
  const role = caller.org ? await roleOf(caller.user.id, caller.org.id) : null;
  const permissions = caller.org
    ? Object.fromEntries(PERMISSIONS.map((p) => [p, can(role, p) && (!caller.scope || scopeAllows(caller.scope, p))]))
    : Object.fromEntries(PERMISSIONS.map((p) => [p, !caller.scope || scopeAllows(caller.scope, p)]));
  const project = caller.projectId && caller.org ? await projectById(caller.org.id, caller.projectId) : null;
  const app = caller.appId && project ? await appById(project.id, caller.appId) : null;
  return {
    user: { id: caller.user.id, name: caller.user.name, email: caller.user.email },
    organization: caller.org,
    organizations: caller.allOrgs ? caller.orgs : undefined,
    role,
    role_label: role ? ROLE_INFO[role]?.label ?? role : null,
    scope: caller.scope,
    permissions,
    token: caller.tokenId,
    project: project ? { id: project.id, name: project.name } : null,
    app: app ? { id: app.id, name: app.name, registry_id: app.registryId } : null,
  };
}

const DIRECTORY = new Set(["projects", "teams", "members", "teams/members", "projects/team", "members/role"]);

async function directory(path: string, req: Request, caller: Caller): Promise<Response> {
  const org = requestedOrg(req, caller);
  if (!org && path === "projects") {
    const all = await Promise.all(caller.orgs.map(async (o) => (await projectsDirectory(o.id, caller.projectId, caller.appId)).map((p) => ({ ...p, organization: { id: o.id, name: o.name } }))));
    return Response.json(all.flat());
  }
  if (!org) return Response.json({ detail: "this token spans every organization: send X-Organization: <id or slug>" }, { status: 400 });
  if (path === "projects") return Response.json(await projectsDirectory(org.id, caller.projectId, caller.appId));
  if (path === "teams") return Response.json(await teamsDirectory(org.id));
  if (path === "members") return Response.json(await membersDirectory(org.id));
  return Response.json({ detail: `GET /api/v1/${path} is not exposed` }, { status: 404 });
}

async function manage(path: string, req: Request, caller: Caller): Promise<Response> {
  const org = requestedOrg(req, caller);
  if (!org) return Response.json({ detail: "this token spans every organization: send X-Organization: <id or slug>" }, { status: 400 });
  const permission: Permission = path === "projects" || path === "projects/team" ? "project.manage" : "org.manage";
  const role = await roleOf(caller.user.id, org.id);
  if (!can(role, permission)) return Response.json({ detail: `your role (${role ?? "none"}) lacks ${permission}` }, { status: 403 });
  if (caller.scope && !scopeAllows(caller.scope, permission)) return Response.json({ detail: `the token's scope (${caller.scope.join(" ")}) does not allow ${permission}` }, { status: 403 });
  if (caller.projectId || caller.appId) return Response.json({ detail: "a token limited to a project or app cannot manage the organization" }, { status: 403 });
  const body = (await req.json().catch(() => ({}))) as Record<string, string | null | undefined>;
  const text = (key: string) => (typeof body[key] === "string" ? (body[key] as string).trim() : "");

  try {
    if (path === "projects") {
      if (!text("name")) return Response.json({ detail: "name is required" }, { status: 400 });
      const project = await createProject(org.id, text("name"), text("description"));
      return Response.json({ id: project.id, name: project.name, slug: project.slug }, { status: 201 });
    }
    if (path === "teams") {
      const team = await createTeam(org.id, text("name"), text("description"));
      return Response.json({ id: team.id, name: team.name, slug: team.slug }, { status: 201 });
    }
    if (path === "teams/members") {
      await addTeamMember(org.id, text("team_id"), text("user_id"));
      return Response.json({ ok: true });
    }
    if (path === "projects/team") {
      await assignProjectTeam(org.id, text("project_id"), text("team_id") || null);
      return Response.json({ ok: true });
    }
    if (path === "members/role") {
      if (!isRole(text("role"))) return Response.json({ detail: `role must be one of ${ROLES.join(", ")}` }, { status: 400 });
      const member = (await membersOf(org.id)).find((m) => m.userId === text("user_id"));
      if (!member) return Response.json({ detail: "member not found" }, { status: 404 });
      await setMemberRole(org.id, member.id, text("role") as Role);
      return Response.json({ ok: true });
    }
  } catch (e) {
    return Response.json({ detail: (e as Error).message }, { status: 400 });
  }
  return Response.json({ detail: `POST /api/v1/${path} is not exposed` }, { status: 404 });
}

function withinReach(caller: Caller, app: { id: string; projectId: string }): boolean {
  if (caller.appId) return app.id === caller.appId;
  if (caller.projectId) return app.projectId === caller.projectId;
  return true;
}

async function issue(req: Request, caller: Caller): Promise<Response> {
  if (req.method !== "POST") return Response.json({ detail: "POST /api/v1/tokens" }, { status: 405 });
  if (caller.scope || !caller.sessionToken) return Response.json({ detail: "a token cannot mint another token; sign in again" }, { status: 403 });
  const body = (await req.json().catch(() => ({}))) as { scope?: string; name?: string };
  const grant = parseGrant(body.scope);
  if (grant.scope.length === 0) return Response.json({ detail: "scope must include at least one of read, write, release, admin" }, { status: 400 });
  const name = (body.name ?? "").trim().slice(0, 80) || "cli";
  let issued;
  try {
    issued = await authApi.issueToken({ token: caller.sessionToken }, { name, scope: body.scope ?? "", organization_id: grant.organizationId ?? undefined, project_id: grant.projectId, app_id: grant.appId });
  } catch (e) {
    if (isAuthError(e)) return Response.json({ detail: e.message }, { status: e.status });
    throw e;
  }
  const claims = await authApi.verifyToken(issued.token, null);
  const organization = claims.organization ? { id: claims.organization.id, name: claims.organization.name, slug: claims.organization.slug } : null;
  const project = claims.project_id ? await projectById(organization?.id ?? "", claims.project_id) : null;
  const app = claims.app_id && project ? await appById(project.id, claims.app_id) : null;
  return Response.json({ token: issued.token, token_type: "Bearer", id: issued.id, scope: formatGrant({ scope: issued.scope as Scope[], organizationId: organization?.id ?? "*", projectId: claims.project_id ?? null, appId: claims.app_id ?? null }), expires_at: issued.expires_at, organization, organizations: organization ? undefined : caller.orgs, project: project ? { id: project.id, name: project.name } : null, app: app ? { id: app.id, name: app.name } : null });
}

type Ctx = { params: Promise<{ path: string[] }> };

export async function GET(req: Request, ctx: Ctx) { return proxy(req, (await ctx.params).path); }
export async function POST(req: Request, ctx: Ctx) { return proxy(req, (await ctx.params).path); }
export async function PUT(req: Request, ctx: Ctx) { return proxy(req, (await ctx.params).path); }
export async function DELETE(req: Request, ctx: Ctx) { return proxy(req, (await ctx.params).path); }
