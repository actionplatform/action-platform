import { client, type Schemas, unwrap } from "@/lib/api";

export const projects = {
  projects: async (organizationId: string | null = null) => unwrap(await client.GET("/api/v1/projects", { headers: organizationId ? { "X-Organization": organizationId } : {} })),
  createProject: async (name: string, description = "") => unwrap(await client.POST("/api/v1/projects", { body: { name, description } })),
  deleteProject: async (id: string, repositories = false) =>
    unwrap(await client.DELETE("/api/v1/projects/{project_id}", { params: { path: { project_id: id }, query: { repositories } } })),
  assignProjectTeam: async (projectId: string, teamId: string | null) => unwrap(await client.POST("/api/v1/projects/team", { body: { project_id: projectId, team_id: teamId } })),
  addApp: async (projectId: string, url: string, install: { type: string; language?: string | null; ci?: string | null } | null) =>
    unwrap(await client.POST("/api/v1/projects/{project_id}/apps", { params: { path: { project_id: projectId } }, body: { url, install } })),
  initApp: async (projectId: string, body: Schemas["InitAppInProject"]) =>
    unwrap(await client.POST("/api/v1/projects/{project_id}/apps/init", { params: { path: { project_id: projectId } }, body })),
  deleteApp: async (projectId: string, appId: string, repository = false) =>
    unwrap(await client.DELETE("/api/v1/projects/{project_id}/apps/{app_id}", { params: { path: { project_id: projectId, app_id: appId }, query: { repository } } })),
  setAppHost: async (projectId: string, appId: string, sourceHostId: string | null) =>
    unwrap(await client.PUT("/api/v1/projects/{project_id}/apps/{app_id}/host", { params: { path: { project_id: projectId, app_id: appId } }, body: { source_host_id: sourceHostId } })),
  imports: async (projectId: string, appId: string) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/imports", { params: { path: { project_id: projectId, app_id: appId } } })),
  syncImports: async (projectId: string, appId: string) =>
    unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/imports", { params: { path: { project_id: projectId, app_id: appId } } })),
  githubOrganizations: async (host: string) => unwrap(await client.GET("/api/v1/import/github/organizations", { params: { query: { host } } })),
  githubOrganization: async (host: string, login: string) =>
    unwrap(await client.GET("/api/v1/import/github/organizations/{login}", { params: { path: { login }, query: { host } } })),
  importGithub: async (body: Schemas["ImportRequest"]) => unwrap(await client.POST("/api/v1/import/github", { body })),
};
