import createClient from "openapi-fetch";
import type { components, paths } from "./api.d";

export const API_BASE = process.env.AP_API ?? "http://127.0.0.1:7788";

export const client = createClient<paths>({ baseUrl: API_BASE, cache: "no-store" });

export type Schemas = components["schemas"];
export type AppRow = Schemas["AppRow"];
export type AppDetail = Schemas["AppDetail"];
export type GitflowReport = Schemas["GitflowReport"];
export type Commit = Schemas["Commit"];
export type Branch = Schemas["Branch"];
export type Matrix = Schemas["Matrix"];
export type ReleasePreview = Schemas["ReleasePreview"];
export type InitRequest = Schemas["InitRequest"];
export type SourceCredentials = Schemas["SourceCredentials"];
export type InitResult = Schemas["InitResult"];
export type DeployResult = Schemas["DeployResult"];
export type Release = Schemas["Release"];
export type BranchResult = Schemas["BranchResult"];
export type PullRequestProposal = Schemas["PullRequestProposal"];
export type PullRequestResult = Schemas["PullRequestResult"];
export type Diagnosis = Schemas["Diagnosis"];

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function unwrap<T>(res: { data?: T; error?: unknown; response: Response }): T {
  if (res.error !== undefined || !res.response.ok) {
    const detail = (res.error as { detail?: string } | undefined)?.detail;
    throw new ApiError(res.response.status, detail ?? res.response.statusText);
  }
  return res.data as T;
}

export const api = {
  version: async () => unwrap(await client.GET("/api/version")),
  matrix: async () => unwrap(await client.GET("/api/matrix")),
  gitflowRules: async () => unwrap(await client.GET("/api/gitflow/rules")),
  apps: {
    list: async () => unwrap(await client.GET("/api/apps")),
    add: async (url: string, name?: string) => unwrap(await client.POST("/api/apps", { body: { url, name } })),
    init: async (body: InitRequest) => unwrap(await client.POST("/api/apps/init", { body })),
    push: async (id: string, priv = false, credentials: SourceCredentials | null = null) =>
      unwrap(await client.POST("/api/apps/{id}/push", { params: { path: { id } }, body: { private: priv, credentials } })),
    sync: async (id: string) =>
      unwrap(await client.POST("/api/apps/{id}/sync", { params: { path: { id } } })),
    remove: async (id: string) =>
      unwrap(await client.DELETE("/api/apps/{id}", { params: { path: { id } } })),
    get: async (id: string) =>
      unwrap(await client.GET("/api/apps/{id}", { params: { path: { id } } })),
    gitflow: async (id: string) =>
      unwrap(await client.GET("/api/apps/{id}/gitflow", { params: { path: { id } } })),
    commits: async (id: string, limit = 20) =>
      unwrap(await client.GET("/api/apps/{id}/commits", { params: { path: { id }, query: { limit } } })),
    tags: async (id: string) =>
      unwrap(await client.GET("/api/apps/{id}/tags", { params: { path: { id } } })),
    startBranch: async (id: string, body: { kind: string; code: string; slug: string | null; push: boolean; credentials: SourceCredentials | null }) =>
      unwrap(await client.POST("/api/apps/{id}/branches", { params: { path: { id } }, body })),
    checkout: async (id: string, branch: string) =>
      unwrap(await client.POST("/api/apps/{id}/checkout", { params: { path: { id } }, body: { branch } })),
    proposePullRequest: async (id: string, base?: string, title?: string) =>
      unwrap(await client.GET("/api/apps/{id}/pull-request", { params: { path: { id }, query: { base, title } } })),
    openPullRequest: async (id: string, body: { base: string | null; title: string | null; body: string | null; draft: boolean; credentials: SourceCredentials | null }) =>
      unwrap(await client.POST("/api/apps/{id}/pull-request", { params: { path: { id } }, body })),
    manifest: async (id: string) =>
      unwrap(await client.GET("/api/apps/{id}/manifest", { params: { path: { id } } })),
    writeManifest: async (id: string, content: string) =>
      unwrap(await client.PUT("/api/apps/{id}/manifest", { params: { path: { id } }, body: { content } })),
    setCloud: async (id: string, target: string) =>
      unwrap(await client.POST("/api/apps/{id}/cloud", { params: { path: { id } }, body: { target } })),
    addService: async (id: string, name: string, provider: string | null) =>
      unwrap(await client.POST("/api/apps/{id}/services", { params: { path: { id } }, body: { name, provider } })),
    commit: async (id: string, body: { message: string; push: boolean; branch: { kind: string; code: string; slug: string | null } | null; pull_request: boolean; credentials: SourceCredentials | null }) =>
      unwrap(await client.POST("/api/apps/{id}/commit", { params: { path: { id } }, body })),
    releases: async (id: string) =>
      unwrap(await client.GET("/api/apps/{id}/releases", { params: { path: { id } } })),
    branches: async (id: string) =>
      unwrap(await client.GET("/api/apps/{id}/branches", { params: { path: { id } } })),
    release: async (id: string, level: string, dry_run: boolean, credentials: SourceCredentials | null = null, branch: string | null = null) =>
      unwrap(await client.POST("/api/apps/{id}/release", { params: { path: { id } }, body: { level, dry_run, credentials, branch } })),
    deploy: async (id: string, stage: string | null, dry_run: boolean) =>
      unwrap(await client.POST("/api/apps/{id}/deploy", { params: { path: { id } }, body: { stage, dry_run } })),
    diagnose: async (id: string, stage?: string) =>
      unwrap(await client.GET("/api/apps/{id}/diagnose", { params: { path: { id }, query: stage ? { stage } : {} } })),
  },
};
