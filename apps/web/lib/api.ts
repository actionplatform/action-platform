import createClient from "openapi-fetch";
import { cookies } from "next/headers";
import { API_TIMEOUT_MS } from "./timeouts";
import type { components, paths } from "./api.d";

export const API_BASE = (process.env.AP_API ?? "http://127.0.0.1:7788").replace(/\/$/, "");

const OPEN = new Set([`${API_BASE}/api/version`]);
const COOKIE = "better-auth.session_token";

async function sessionCookieValue(): Promise<string | null> {
  try {
    const jar = await cookies();
    return jar.get(`__Secure-${COOKIE}`)?.value ?? jar.get(COOKIE)?.value ?? null;
  } catch {
    return null;
  }
}

function throughGate(url: string): string {
  if (OPEN.has(url.split("?")[0]) || url.startsWith(`${API_BASE}/api/v1/`) || url.startsWith(`${API_BASE}/api/auth/`)) return url;
  return url.replace(`${API_BASE}/api/`, `${API_BASE}/api/v1/`);
}

export const client = createClient<paths>({
  baseUrl: API_BASE,
  cache: "no-store",
  fetch: async (input) => {
    const request = new Request(throughGate(input.url), input);
    const cookie = await sessionCookieValue();
    if (cookie && !request.headers.has("X-Session-Cookie") && !request.headers.has("X-Session-Token")) request.headers.set("X-Session-Cookie", cookie);
    return fetch(request, { signal: AbortSignal.timeout(API_TIMEOUT_MS) });
  },
});

export type Schemas = components["schemas"];
export type AppRow = Schemas["AppRow"];
export type AppDetail = Schemas["AppDetail"];
export type GitflowReport = Schemas["GitflowReport"];
export type Commit = Schemas["Commit"];
export type Branch = Schemas["Branch"];
export type Matrix = Schemas["Matrix"];
export type ReleasePreview = Schemas["ReleasePreview"];
export type InitRequest = Schemas["InitRequest"];
export type SourceSpec = Schemas["SourceSpec"];
export type SourceCredentials = Schemas["SourceCredentials"];
export type InitResult = Schemas["InitResult"];
export type DeployResult = Schemas["DeployResult"];
export type Release = Schemas["Release"];
export type BranchResult = Schemas["BranchResult"];
export type PullRequestProposal = Schemas["PullRequestProposal"];
export type PullRequestResult = Schemas["PullRequestResult"];
export type Diagnosis = Schemas["Diagnosis"];

export class ApiError extends Error {
  constructor(public status: number, message: string, public code: string | null = null) {
    super(message);
  }
}

export function unwrap<T>(res: { data?: T; error?: unknown; response: Response }): T {
  if (res.error !== undefined || !res.response.ok) {
    const body = res.error as { detail?: string | { code?: string; detail?: string }; error?: string } | undefined;
    const detail = body?.detail;
    if (detail && typeof detail === "object") throw new ApiError(res.response.status, detail.detail ?? res.response.statusText, detail.code ?? null);
    throw new ApiError(res.response.status, detail ?? res.response.statusText, body?.error ?? null);
  }
  return res.data as T;
}

type Queued = { job: string; status: string; poll: string };

export const api = {
  version: async () => unwrap(await client.GET("/api/version")),
  matrix: async () => unwrap(await client.GET("/api/matrix")),
  gitflowRules: async () => unwrap(await client.GET("/api/gitflow/rules")),
  apps: {
    list: async (projectId: string) => unwrap(await client.GET("/api/v1/projects/{project_id}/apps", { params: { path: { project_id: projectId } } })),
    sync: async (projectId: string, id: string, reset = false) =>
      unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/sync", { params: { path: { project_id: projectId, app_id: id } }, body: { reset } })) as unknown as Queued,
    get: async (projectId: string, id: string) =>
      unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}", { params: { path: { project_id: projectId, app_id: id } } })),
    gitflow: async (projectId: string, id: string) =>
      unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/gitflow", { params: { path: { project_id: projectId, app_id: id } } })),
    commits: async (projectId: string, id: string, limit = 20) =>
      unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/commits", { params: { path: { project_id: projectId, app_id: id }, query: { limit } } })),
    tags: async (projectId: string, id: string) =>
      unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/tags", { params: { path: { project_id: projectId, app_id: id } } })),
    startBranch: async (projectId: string, id: string, body: { kind: string; code: string; slug: string | null; push: boolean }) =>
      unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/branches", { params: { path: { project_id: projectId, app_id: id } }, body })),
    planBranch: async (projectId: string, id: string, kind: string, code: string, slug: string | null) =>
      unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/branches/plan", { params: { path: { project_id: projectId, app_id: id }, query: { kind, code, slug: slug ?? undefined } } })),
    checkout: async (projectId: string, id: string, branch: string) =>
      unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/checkout", { params: { path: { project_id: projectId, app_id: id } }, body: { branch } })),
    proposePullRequest: async (projectId: string, id: string, base?: string, title?: string) =>
      unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/pull-request", { params: { path: { project_id: projectId, app_id: id }, query: { base, title } } })),
    openPullRequest: async (projectId: string, id: string, body: { base: string | null; title: string | null; body: string | null; draft: boolean }) =>
      unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/pull-request", { params: { path: { project_id: projectId, app_id: id } }, body })),
    manifest: async (projectId: string, id: string) =>
      unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/manifest", { params: { path: { project_id: projectId, app_id: id } } })),
    writeManifest: async (projectId: string, id: string, content: string) =>
      unwrap(await client.PUT("/api/v1/projects/{project_id}/apps/{app_id}/manifest", { params: { path: { project_id: projectId, app_id: id } }, body: { content } })),
    exportManifest: async (projectId: string, id: string) =>
      unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/manifest/export", { params: { path: { project_id: projectId, app_id: id } } })),
    setCloud: async (projectId: string, id: string, target: string, source: string | null = null) =>
      unwrap(await client.PUT("/api/v1/projects/{project_id}/apps/{app_id}/cloud", { params: { path: { project_id: projectId, app_id: id } }, body: { target, source: source as never } })),
    addService: async (projectId: string, id: string, name: string, provider: string | null, source: string | null = null) =>
      unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/services", { params: { path: { project_id: projectId, app_id: id } }, body: { name, provider, source: source as never } })),
    changes: async (projectId: string, id: string) => unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/changes", { params: { path: { project_id: projectId, app_id: id } } })),
    install: async (projectId: string, id: string, spec: { type: string; language?: string | null; ci?: string | null } = { type: "web" }) => unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/install", { params: { path: { project_id: projectId, app_id: id } }, body: spec })),
    discard: async (projectId: string, id: string) => unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/discard", { params: { path: { project_id: projectId, app_id: id } } })),
    commit: async (projectId: string, id: string, body: { message: string; push: boolean; branch: { kind: string; code: string; slug: string | null } | null; pull_request: boolean }) =>
      unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/commit", { params: { path: { project_id: projectId, app_id: id } }, body })),
    releases: async (projectId: string, id: string) =>
      unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/versions", { params: { path: { project_id: projectId, app_id: id } } })),
    branches: async (projectId: string, id: string) =>
      unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/branches", { params: { path: { project_id: projectId, app_id: id } } })),
    nextVersion: async (projectId: string, id: string, level: string, branch: string | null = null, component: string | null = null) =>
      unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/next-version", { params: { path: { project_id: projectId, app_id: id }, query: { level, branch: branch ?? undefined, component: component ?? undefined } } })),
    release: async (projectId: string, id: string, level: string, dry_run: boolean, branch: string | null = null, extra: { name?: string | null; notes?: string | null; latest?: boolean; component?: string | null } = {}) =>
      unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/release", { params: { path: { project_id: projectId, app_id: id } }, body: { level, dry_run, branch, latest: true, ...extra } })),
    releaseAsync: async (projectId: string, id: string, level: string, branch: string | null = null, extra: { name?: string | null; notes?: string | null; latest?: boolean; component?: string | null } = {}) =>
      unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/release", { params: { path: { project_id: projectId, app_id: id } }, body: { level, dry_run: false, branch, latest: true, ...extra } })) as unknown as Queued,
    preflight: async (projectId: string, id: string, stage: string | null, version: string | null = null, force = false) =>
      unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/deploy", { params: { path: { project_id: projectId, app_id: id } }, body: { stage, dry_run: true, version, force } })),
    deployAsync: async (projectId: string, id: string, stage: string | null, version: string | null = null, force = false) =>
      unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/deploy", { params: { path: { project_id: projectId, app_id: id } }, body: { stage, dry_run: false, version, force } })) as unknown as Queued,
    diagnose: async (projectId: string, id: string, stage?: string) =>
      unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/diagnose", { params: { path: { project_id: projectId, app_id: id }, query: stage ? { stage } : {} } })),
  },
};
