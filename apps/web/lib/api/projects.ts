import { client, type Schemas, unwrap } from "@/lib/api";

export const projects = {
  projects: async (organizationId: string | null = null) => unwrap(await client.GET("/api/v1/projects", { headers: organizationId ? { "X-Organization": organizationId } : {} })),
  createProject: async (name: string, description = "") => unwrap(await client.POST("/api/v1/projects", { body: { name, description } })),
  deleteProject: async (id: string, repositories = false, cloud = false) =>
    unwrap(await client.DELETE("/api/v1/projects/{project_id}", { params: { path: { project_id: id }, query: { repositories, cloud } } })),
  assignProjectTeam: async (projectId: string, teamId: string | null) => unwrap(await client.POST("/api/v1/projects/team", { body: { project_id: projectId, team_id: teamId } })),
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
  imports: async (projectId: string, appId: string) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/imports", { params: { path: { project_id: projectId, app_id: appId } } })),
  syncImports: async (projectId: string, appId: string) =>
    unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/imports", { params: { path: { project_id: projectId, app_id: appId } } })),
  linkCi: async (projectId: string, appId: string, ciHostId: string | null, job: string) =>
    unwrap(await client.PUT("/api/v1/projects/{project_id}/apps/{app_id}/ci", { params: { path: { project_id: projectId, app_id: appId } }, body: { ci_host_id: ciHostId, job } })),
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
  timeline: async (projectId: string, appId: string, tag: string) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/releases/{tag}/timeline", { params: { path: { project_id: projectId, app_id: appId, tag } } })),
  githubOrganizations: async (host: string) => unwrap(await client.GET("/api/v1/import/github/organizations", { params: { query: { host } } })),
  githubOrganization: async (host: string, login: string) =>
    unwrap(await client.GET("/api/v1/import/github/organizations/{login}", { params: { path: { login }, query: { host } } })),
  importGithub: async (body: Schemas["ImportRequest"]) => unwrap(await client.POST("/api/v1/import/github", { body })),
};
