// Typed client over the Python API. Types come from lib/api.d.ts, generated
// with `npm run api:types` while `action-platform api` is running — the
// Python side is the contract, the same way tRPC would be in a TS backend.
import createClient from "openapi-fetch";
import type { components, paths } from "./api.d";

export const API_BASE = process.env.AP_API ?? "http://127.0.0.1:7788";

export const client = createClient<paths>({ baseUrl: API_BASE, cache: "no-store" });

export type Schemas = components["schemas"];
export type ProjectRow = Schemas["ProjectRow"];
export type ProjectDetail = Schemas["ProjectDetail"];
export type GitflowReport = Schemas["GitflowReport"];
export type Commit = Schemas["Commit"];
export type Branch = Schemas["Branch"];
export type Matrix = Schemas["Matrix"];
export type ReleasePreview = Schemas["ReleasePreview"];
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
  projects: {
    list: async () => unwrap(await client.GET("/api/projects")),
    add: async (path: string) => unwrap(await client.POST("/api/projects", { body: { path } })),
    remove: async (id: string) =>
      unwrap(await client.DELETE("/api/projects/{id}", { params: { path: { id } } })),
    get: async (id: string) =>
      unwrap(await client.GET("/api/projects/{id}", { params: { path: { id } } })),
    gitflow: async (id: string) =>
      unwrap(await client.GET("/api/projects/{id}/gitflow", { params: { path: { id } } })),
    commits: async (id: string, limit = 20) =>
      unwrap(await client.GET("/api/projects/{id}/commits", { params: { path: { id }, query: { limit } } })),
    tags: async (id: string) =>
      unwrap(await client.GET("/api/projects/{id}/tags", { params: { path: { id } } })),
    branches: async (id: string) =>
      unwrap(await client.GET("/api/projects/{id}/branches", { params: { path: { id } } })),
    release: async (id: string, level: string, dry_run: boolean) =>
      unwrap(await client.POST("/api/projects/{id}/release", { params: { path: { id } }, body: { level, dry_run } })),
    deploy: async (id: string, stage: string | null, dry_run: boolean) =>
      unwrap(await client.POST("/api/projects/{id}/deploy", { params: { path: { id } }, body: { stage, dry_run } })),
    diagnose: async (id: string, stage?: string) =>
      unwrap(await client.GET("/api/projects/{id}/diagnose", { params: { path: { id }, query: stage ? { stage } : {} } })),
  },
};
