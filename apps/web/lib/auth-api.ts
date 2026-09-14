import { ApiError, client, type Schemas, unwrap } from "./api";

export type Identity = Schemas["IdentityOut"];
export type Signed = Schemas["Signed"];
export type BrowserSessionRow = Schemas["BrowserSessionOut"];
export type DeviceRequest = Schemas["DeviceRequestOut"];
export type TokenRow = Schemas["TokenOut"];
export type TokenIssued = Schemas["TokenIssued"];
export type TokenClaims = Schemas["TokenClaimsOut"];
export type GrantIn = Schemas["GrantIn"];

type Session = { token: string } | { cookie: string };

function sessionHeaders(session: Session): Record<string, string> {
  return "token" in session ? { "X-Session-Token": session.token } : { "X-Session-Cookie": session.cookie };
}

function clientHeaders(ip: string | null): Record<string, string> {
  return ip ? { "X-Forwarded-For": ip } : {};
}

export function isAuthError(e: unknown, ...statuses: number[]): e is ApiError {
  return e instanceof ApiError && (statuses.length === 0 || statuses.includes(e.status));
}

export const authApi = {
  status: async () => unwrap(await client.GET("/api/auth/status")),
  signUp: async (body: { name: string; email: string; password: string; invitation_id?: string | null }, ip: string | null) =>
    unwrap(await client.POST("/api/auth/sign-up", { body, headers: clientHeaders(ip) })),
  signIn: async (body: { email: string; password: string; ip_address?: string | null; user_agent?: string | null }, ip: string | null) =>
    unwrap(await client.POST("/api/auth/sign-in", { body, headers: clientHeaders(ip) })),
  signOut: async (session: Session) => unwrap(await client.POST("/api/auth/sign-out", { headers: sessionHeaders(session) })),
  session: async (session: Session) => unwrap(await client.GET("/api/auth/session", { headers: sessionHeaders(session) })),
  setActiveOrganization: async (session: Session, organizationId: string) =>
    unwrap(await client.POST("/api/auth/session/organization", { body: { organization_id: organizationId }, headers: sessionHeaders(session) })),
  sessions: async (session: Session) => unwrap(await client.GET("/api/auth/sessions", { headers: sessionHeaders(session) })),
  revokeSession: async (session: Session, id: string) => unwrap(await client.DELETE("/api/auth/sessions/{id}", { params: { path: { id } }, headers: sessionHeaders(session) })),
  createOrganization: async (session: Session, body: { name: string; slug: string; git_author_name?: string | null; git_author_email?: string | null }) =>
    unwrap(await client.POST("/api/auth/organizations", { body, headers: sessionHeaders(session) })),
  addMember: async (session: Session, body: { organization_id: string; name: string; email: string; password: string; role: string }) =>
    unwrap(await client.POST("/api/auth/members", { body, headers: sessionHeaders(session) })),
  deviceCode: async (body: { client_id?: string | null; scope?: string | null }, ip: string | null) =>
    unwrap(await client.POST("/api/auth/device/code", { body, headers: clientHeaders(ip) })),
  deviceToken: async (body: { grant_type: string; device_code: string; client_id?: string | null }, ip: string | null) =>
    unwrap(await client.POST("/api/auth/device/token", { body, headers: clientHeaders(ip) })),
  deviceRequest: async (session: Session, userCode: string) =>
    unwrap(await client.GET("/api/auth/device", { params: { query: { user_code: userCode } }, headers: sessionHeaders(session) })),
  deviceApprove: async (session: Session, userCode: string, grant: GrantIn | null) =>
    unwrap(await client.POST("/api/auth/device/approve", { body: { user_code: userCode, grant }, headers: sessionHeaders(session) })),
  deviceDeny: async (session: Session, userCode: string) =>
    unwrap(await client.POST("/api/auth/device/deny", { body: { user_code: userCode, grant: null }, headers: sessionHeaders(session) })),
  issueToken: async (session: Session, body: { name: string; scope: string; organization_id?: string | null; project_id?: string | null; app_id?: string | null }) =>
    unwrap(await client.POST("/api/auth/tokens", { body, headers: sessionHeaders(session) })),
  tokens: async (session: Session, organizationId: string | null = null) =>
    unwrap(await client.GET("/api/auth/tokens", { params: { query: organizationId ? { organization_id: organizationId } : {} }, headers: sessionHeaders(session) })),
  revokeToken: async (session: Session, id: string) => unwrap(await client.DELETE("/api/auth/tokens/{id}", { params: { path: { id } }, headers: sessionHeaders(session) })),
  verifyToken: async (token: string, clientName: string | null) => unwrap(await client.POST("/api/auth/tokens/verify", { body: { token, client: clientName } })),
};
