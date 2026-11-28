import { client, type Schemas, unwrap } from "@/lib/api";

export const projects = {
  projects: async (organizationId: string | null = null) => unwrap(await client.GET("/api/v1/projects", { headers: organizationId ? { "X-Organization": organizationId } : {} })) as Schemas["ProjectRow"][],
  createProject: async (name: string, description = "") => unwrap(await client.POST("/api/v1/projects", { body: { name, description } })),
  deleteProject: async (id: string, repositories = false, cloud = false) =>
    unwrap(await client.DELETE("/api/v1/projects/{project_id}", { params: { path: { project_id: id }, query: { repositories, cloud } } })),
  assignProjectTeam: async (projectId: string, teamId: string | null) => unwrap(await client.PUT("/api/v1/projects/{project_id}/team", { params: { path: { project_id: projectId } }, body: { team_id: teamId } })),
  addApp: async (projectId: string, url: string, install: { type: string; language?: string | null; ci?: string | null } | null) =>
    unwrap(await client.POST("/api/v1/projects/{project_id}/apps", { params: { path: { project_id: projectId } }, body: { url, install } })),
  initApp: async (projectId: string, body: Schemas["InitAppInProject"]) =>
    unwrap(await client.POST("/api/v1/projects/{project_id}/apps/init", { params: { path: { project_id: projectId } }, body })),
  deleteApp: async (projectId: string, appId: string, repository = false, cloud = false) =>
    unwrap(await client.DELETE("/api/v1/projects/{project_id}/apps/{app_id}", { params: { path: { project_id: projectId, app_id: appId }, query: { repository, cloud } } })),
  setAppHost: async (projectId: string, appId: string, sourceHostId: string | null) =>
    unwrap(await client.PUT("/api/v1/projects/{project_id}/apps/{app_id}/host", { params: { path: { project_id: projectId, app_id: appId } }, body: { source_host_id: sourceHostId } })),
  releasesPage: async (projectId: string, appId: string, page: number, per: number) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/releases", { params: { path: { project_id: projectId, app_id: appId }, query: { page, per } } })),
  pullRequestsPage: async (projectId: string, appId: string, page: number, per: number) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/pull-requests", { params: { path: { project_id: projectId, app_id: appId }, query: { page, per } } })),
  ci: async (projectId: string, appId: string, page = 1, per = 10) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/ci", { params: { path: { project_id: projectId, app_id: appId }, query: { page, per } } })),
  startCi: async (projectId: string, appId: string, ref: string) =>
    unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/ci/run", { params: { path: { project_id: projectId, app_id: appId } }, body: { ref } })),
  syncCi: async (projectId: string, appId: string, page = 1, per = 10) =>
    unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/ci/sync", { params: { path: { project_id: projectId, app_id: appId }, query: { page, per } } })),
  pipelines: async (projectId: string, appId: string, job: string | null, status: string | null, limit = 50) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/ci/runs", { params: { path: { project_id: projectId, app_id: appId }, query: { job: job ?? undefined, status: status ?? undefined, limit } } })),
  deployRuns: async (projectId: string, appId: string, q: { stage: string | null; version: string; since: string | null; until: string | null; urls: string[] }) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/ci/deploy-runs", { params: { path: { project_id: projectId, app_id: appId }, query: { stage: q.stage ?? undefined, version: q.version, since: q.since ?? undefined, until: q.until ?? undefined, url: q.urls } } })),
  pipelineRun: async (projectId: string, appId: string, job: string, number: number) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/ci/runs/{number}", { params: { path: { project_id: projectId, app_id: appId, number }, query: { job } } })),
  pipelineLog: async (projectId: string, appId: string, job: string, number: number, start: number, node: string | null) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/ci/runs/{number}/log", { params: { path: { project_id: projectId, app_id: appId, number }, query: { job, start, node: node ?? undefined } } })),
  pipelineTests: async (projectId: string, appId: string, job: string, number: number) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/ci/runs/{number}/tests", { params: { path: { project_id: projectId, app_id: appId, number }, query: { job } } })),
  pipelineArtifacts: async (projectId: string, appId: string, job: string, number: number) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/ci/runs/{number}/artifacts", { params: { path: { project_id: projectId, app_id: appId, number }, query: { job } } })),
  imports: async (projectId: string, appId: string) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/imports", { params: { path: { project_id: projectId, app_id: appId } } })),
  syncImports: async (projectId: string, appId: string) =>
    unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/imports", { params: { path: { project_id: projectId, app_id: appId } } })),
  linkCi: async (projectId: string, appId: string, ciHostId: string | null, job: string) =>
    unwrap(await client.PUT("/api/v1/projects/{project_id}/apps/{app_id}/ci", { params: { path: { project_id: projectId, app_id: appId } }, body: { ci_host_id: ciHostId, job } })),
  protection: async (projectId: string, appId: string, refresh = false) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/protection", { params: { path: { project_id: projectId, app_id: appId }, query: { refresh } } })),
  setProtection: async (projectId: string, appId: string, enforce: boolean | null) =>
    unwrap(await client.PUT("/api/v1/projects/{project_id}/apps/{app_id}/protection", { params: { path: { project_id: projectId, app_id: appId } }, body: { enforce } })),
  applyProtection: async (projectId: string, appId: string) =>
    unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/protection/apply", { params: { path: { project_id: projectId, app_id: appId } } })),
  deployments: async (projectId: string, appId: string) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/deployments", { params: { path: { project_id: projectId, app_id: appId } } })),
  syncDeployments: async (projectId: string, appId: string) =>
    unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/deployments/sync", { params: { path: { project_id: projectId, app_id: appId } } })),
  recordDeployment: async (projectId: string, appId: string, body: Schemas["RecordDeploymentRequest"]) =>
    unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/deployments", { params: { path: { project_id: projectId, app_id: appId } }, body })),
  scopes: async (projectId: string, appId: string) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/scopes", { params: { path: { project_id: projectId, app_id: appId } } })),
  createScope: async (projectId: string, appId: string, body: Schemas["ScopeRequest"]) =>
    unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/scopes", { params: { path: { project_id: projectId, app_id: appId } }, body })),
  updateScope: async (projectId: string, appId: string, name: string, body: Schemas["ScopeRequest"]) =>
    unwrap(await client.PUT("/api/v1/projects/{project_id}/apps/{app_id}/scopes/{name}", { params: { path: { project_id: projectId, app_id: appId, name } }, body })),
  deleteScope: async (projectId: string, appId: string, name: string) =>
    unwrap(await client.DELETE("/api/v1/projects/{project_id}/apps/{app_id}/scopes/{name}", { params: { path: { project_id: projectId, app_id: appId, name } } })),
  readiness: async (projectId: string, appId: string, tag: string) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/releases/{tag}/readiness", { params: { path: { project_id: projectId, app_id: appId, tag } } })),
  checkReadiness: async (projectId: string, appId: string, tag: string, stage: string | null = null) =>
    unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/releases/{tag}/readiness", { params: { path: { project_id: projectId, app_id: appId, tag } }, body: { stage } })),
  appActivity: async (projectId: string, appId: string, kind: string | null = null, limit = 50) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/activity", { params: { path: { project_id: projectId, app_id: appId }, query: { kind, limit } } })),
  timeline: async (projectId: string, appId: string, tag: string) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/releases/{tag}/timeline", { params: { path: { project_id: projectId, app_id: appId, tag } } })),
  adoption: async (projectId: string) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/adoption", { params: { path: { project_id: projectId } } })),
  installApps: async (projectId: string, body: Schemas["ProjectInstallRequest"]) =>
    unwrap(await client.POST("/api/v1/projects/{project_id}/install", { params: { path: { project_id: projectId } }, body })),
  importOrganizations: async (host: string) => unwrap(await client.GET("/api/v1/import/{host_id}/organizations", { params: { path: { host_id: host } } })),
  importPreview: async (host: string, login: string) =>
    unwrap(await client.GET("/api/v1/import/{host_id}/organizations/{login}", { params: { path: { host_id: host, login } } })),
  importOrganization: async (body: Schemas["ImportRequest"]) => unwrap(await client.POST("/api/v1/import", { body })),
};
