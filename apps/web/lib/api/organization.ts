import { client, unwrap } from "@/lib/api";

export const organization = {
  me: async () => unwrap(await client.GET("/api/v1/me")),
  access: async () => unwrap(await client.GET("/api/v1/access")),
  organizations: async () => unwrap(await client.GET("/api/v1/organizations")),
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
  gitAuthor: async () => unwrap(await client.GET("/api/v1/settings/git-author")),
  setGitAuthor: async (name: string, email: string) => unwrap(await client.PUT("/api/v1/settings/git-author", { body: { name, email } })),
};
