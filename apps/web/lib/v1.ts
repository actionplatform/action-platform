import { client, type Schemas, unwrap } from "./api";

export type ProjectRow = Schemas["ProjectRow"];
export type TeamRow = Schemas["TeamRow"];
export type MemberRow = Schemas["MemberRow"];
export type InvitationRow = Schemas["InvitationRow"];
export type HostRow = Schemas["HostRow"];
export type OAuthAppRow = Schemas["OAuthAppRow"];
export type TemplateSourceRow = Schemas["TemplateSourceRow"];
export type ImportsRow = Schemas["Imports"];
export type ReleaseRow = Schemas["ReleaseRow"];
export type PullRequestRow = Schemas["PullRequestRow"];
export type JobRow = Schemas["JobOut"];

export const v1 = {
  me: async () => unwrap(await client.GET("/api/v1/me")),
  access: async () => unwrap(await client.GET("/api/v1/access")),
  organizations: async () => unwrap(await client.GET("/api/v1/organizations")),
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
  teams: async () => unwrap(await client.GET("/api/v1/teams")),
  createTeam: async (name: string, description = "") => unwrap(await client.POST("/api/v1/teams", { body: { name, description } })),
  updateTeam: async (id: string, name: string, description = "") => unwrap(await client.PUT("/api/v1/teams/{team_id}", { params: { path: { team_id: id } }, body: { name, description } })),
  deleteTeam: async (id: string) => unwrap(await client.DELETE("/api/v1/teams/{team_id}", { params: { path: { team_id: id } } })),
  addTeamMember: async (teamId: string, userId: string) => unwrap(await client.POST("/api/v1/teams/members", { body: { team_id: teamId, user_id: userId } })),
  removeTeamMember: async (teamId: string, userId: string) =>
    unwrap(await client.DELETE("/api/v1/teams/{team_id}/members/{user_id}", { params: { path: { team_id: teamId, user_id: userId } } })),
  members: async () => unwrap(await client.GET("/api/v1/members")),
  setMemberRole: async (userId: string, role: string) => unwrap(await client.POST("/api/v1/members/role", { body: { user_id: userId, role } })),
  removeMember: async (userId: string) => unwrap(await client.DELETE("/api/v1/members/{user_id}", { params: { path: { user_id: userId } } })),
  invitations: async () => unwrap(await client.GET("/api/v1/invitations")),
  invite: async (email: string, role: string) => unwrap(await client.POST("/api/v1/invitations", { body: { email, role } })),
  cancelInvitation: async (id: string) => unwrap(await client.DELETE("/api/v1/invitations/{id}", { params: { path: { id } } })),
  hosts: async () => unwrap(await client.GET("/api/v1/hosts")),
  addHost: async (body: Schemas["AddHostRequest"]) => unwrap(await client.POST("/api/v1/hosts", { body })),
  removeHost: async (id: string) => unwrap(await client.DELETE("/api/v1/hosts/{host_id}", { params: { path: { host_id: id } } })),
  rotateHostToken: async (id: string, token: string) => unwrap(await client.PUT("/api/v1/hosts/{host_id}/token", { params: { path: { host_id: id } }, body: { token } })),
  setHostOwner: async (id: string, owner: string) => unwrap(await client.PUT("/api/v1/hosts/{host_id}/owner", { params: { path: { host_id: id } }, body: { owner } })),
  hostAccess: async (id: string) => unwrap(await client.GET("/api/v1/hosts/{host_id}/access", { params: { path: { host_id: id } } })),
  oauthApps: async () => unwrap(await client.GET("/api/v1/oauth/apps")),
  saveOAuthApp: async (provider: string, body: Schemas["OAuthAppRequest"]) => unwrap(await client.PUT("/api/v1/oauth/apps/{provider}", { params: { path: { provider } }, body })),
  clearOAuthApp: async (provider: string) => unwrap(await client.DELETE("/api/v1/oauth/apps/{provider}", { params: { path: { provider } } })),
  oauthStart: async (provider: string, origin: string, returnTo: string) =>
    unwrap(await client.POST("/api/v1/oauth/{provider}/start", { params: { path: { provider } }, body: { origin, return_to: returnTo } })),
  oauthCallback: async (provider: string, body: Schemas["OAuthCallbackRequest"]) =>
    unwrap(await client.POST("/api/v1/oauth/{provider}/callback", { params: { path: { provider } }, body })),
  disconnectOAuthHost: async (provider: string, login: string) =>
    unwrap(await client.DELETE("/api/v1/oauth/{provider}/hosts/{login}", { params: { path: { provider, login } } })),
  githubManifest: async (body: Schemas["ManifestRequest"]) => unwrap(await client.POST("/api/v1/oauth/github/manifest", { body })),
  githubManifestCallback: async (body: Schemas["ManifestCallbackRequest"]) => unwrap(await client.POST("/api/v1/oauth/github/manifest/callback", { body })),
  githubInstall: async (origin: string, returnTo: string) => unwrap(await client.POST("/api/v1/oauth/github/install", { body: { origin, return_to: returnTo } })),
  gitAuthor: async () => unwrap(await client.GET("/api/v1/settings/git-author")),
  setGitAuthor: async (name: string, email: string) => unwrap(await client.PUT("/api/v1/settings/git-author", { body: { name, email } })),
  templateSources: async () => unwrap(await client.GET("/api/v1/template-sources")),
  addTemplateSource: async (name: string, url: string, ref: string) => unwrap(await client.POST("/api/v1/template-sources", { body: { name, url, ref } })),
  removeTemplateSource: async (id: string) => unwrap(await client.DELETE("/api/v1/template-sources/{id}", { params: { path: { id } } })),
  job: async (id: string) => unwrap(await client.GET("/api/v1/jobs/{id}", { params: { path: { id } } })),
  jobs: async (app: string) => unwrap(await client.GET("/api/v1/jobs", { params: { query: { app } } })),
};
