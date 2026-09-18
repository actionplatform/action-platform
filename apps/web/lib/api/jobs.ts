import { client, unwrap } from "@/lib/api";

export const jobs = {
  jobsPage: async (app: string, kinds: string, page: number, per: number) => unwrap(await client.GET("/api/v1/jobs/page", { params: { query: { app, kinds, page, per } } })),
  job: async (id: string) => unwrap(await client.GET("/api/v1/jobs/{id}", { params: { path: { id } } })),
  jobLogs: async (id: string, after = 0, limit = 1000) => unwrap(await client.GET("/api/v1/jobs/{id}/logs", { params: { path: { id }, query: { after, limit } } })),
  jobs: async (app: string, kind: string | null = null, limit = 20) => unwrap(await client.GET("/api/v1/jobs", { params: { query: { app, kind, limit } } })),
};
