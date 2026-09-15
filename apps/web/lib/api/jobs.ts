import { client, unwrap } from "@/lib/api";

export const jobs = {
  job: async (id: string) => unwrap(await client.GET("/api/v1/jobs/{id}", { params: { path: { id } } })),
  jobs: async (app: string, kind: string | null = null) => unwrap(await client.GET("/api/v1/jobs", { params: { query: { app, kind } } })),
};
