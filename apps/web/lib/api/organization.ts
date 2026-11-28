import { client, type Schemas, unwrap } from "@/lib/api";
import type { PageQuery, Paged } from "@/lib/page";

export const organization = {
  dashboard: async () => unwrap(await client.GET("/api/v1/dashboard")),
  me: async () => unwrap(await client.GET("/api/v1/me")),
  access: async () => unwrap(await client.GET("/api/v1/access")),
  organizations: async () => unwrap(await client.GET("/api/v1/organizations")),
  teams: async () => unwrap(await client.GET("/api/v1/teams")) as Schemas["TeamRow"][],
  createTeam: async (name: string, description = "") => unwrap(await client.POST("/api/v1/teams", { body: { name, description } })),
  updateTeam: async (id: string, name: string, description = "") => unwrap(await client.PUT("/api/v1/teams/{team_id}", { params: { path: { team_id: id } }, body: { name, description } })),
  deleteTeam: async (id: string) => unwrap(await client.DELETE("/api/v1/teams/{team_id}", { params: { path: { team_id: id } } })),
  addTeamMember: async (teamId: string, userId: string) => unwrap(await client.POST("/api/v1/teams/{team_id}/members", { params: { path: { team_id: teamId } }, body: { user_id: userId } })),
  removeTeamMember: async (teamId: string, userId: string) =>
    unwrap(await client.DELETE("/api/v1/teams/{team_id}/members/{user_id}", { params: { path: { team_id: teamId, user_id: userId } } })),
  members: async () => unwrap(await client.GET("/api/v1/members")) as Schemas["MemberRow"][],
  membersPage: async (q: PageQuery) => unwrap(await client.GET("/api/v1/members", { params: { query: q } })) as Paged<Schemas["MemberRow"]>,
  setMemberRole: async (userId: string, role: string) => unwrap(await client.PATCH("/api/v1/members/{user_id}", { params: { path: { user_id: userId } }, body: { role } })),
  removeMember: async (userId: string) => unwrap(await client.DELETE("/api/v1/members/{user_id}", { params: { path: { user_id: userId } } })),
  invitations: async () => unwrap(await client.GET("/api/v1/invitations")) as Schemas["InvitationRow"][],
  invite: async (email: string, role: string, teamIds: string[] = []) => unwrap(await client.POST("/api/v1/invitations", { body: { email, role, team_ids: teamIds } })),
  resendInvitation: async (id: string) => unwrap(await client.POST("/api/v1/invitations/{id}/resend", { params: { path: { id } } })),
  cancelInvitation: async (id: string) => unwrap(await client.DELETE("/api/v1/invitations/{id}", { params: { path: { id } } })),
  gitAuthor: async () => unwrap(await client.GET("/api/v1/settings/git-author")),
  setGitAuthor: async (name: string, email: string) => unwrap(await client.PUT("/api/v1/settings/git-author", { body: { name, email } })),
  protectionDefault: async () => unwrap(await client.GET("/api/v1/settings/protection")),
  setProtectionDefault: async (enforce: boolean) => unwrap(await client.PUT("/api/v1/settings/protection", { body: { enforce } })),
  deleteOrganization: async (id: string, confirm: string, repositories = false, cloud = false) =>
    unwrap(await client.DELETE("/api/v1/organizations/{organization_id}", { params: { path: { organization_id: id }, query: { confirm, repositories, cloud } } })),
};
