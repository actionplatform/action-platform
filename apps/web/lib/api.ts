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
    branches: async (id: string) =>
      unwrap(await client.GET("/api/apps/{id}/branches", { params: { path: { id } } })),
    release: async (id: string, level: string, dry_run: boolean, credentials: SourceCredentials | null = null) =>
      unwrap(await client.POST("/api/apps/{id}/release", { params: { path: { id } }, body: { level, dry_run, credentials } })),
    deploy: async (id: string, stage: string | null, dry_run: boolean) =>
      unwrap(await client.POST("/api/apps/{id}/deploy", { params: { path: { id } }, body: { stage, dry_run } })),
    diagnose: async (id: string, stage?: string) =>
      unwrap(await client.GET("/api/apps/{id}/diagnose", { params: { path: { id }, query: stage ? { stage } : {} } })),
  },
};
