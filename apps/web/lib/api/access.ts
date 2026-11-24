import { client, type Schemas, unwrap } from "@/lib/api";

export const serviceAccess = {
  accessAudit: async (service?: string) => unwrap(await client.GET("/api/v1/access/audit", { params: { query: { service } } })),
  accessWho: async (query: { person?: string; service?: string }) => unwrap(await client.GET("/api/v1/access/who", { params: { query } })),
  accessSync: async (body: Schemas["app__schemas__service_access__SyncRequest"]) => unwrap(await client.POST("/api/v1/access/sync", { body })),
  accessGrant: async (body: Schemas["GrantRequest"]) => unwrap(await client.POST("/api/v1/access/grant", { body })),
  accessRevoke: async (body: Schemas["RevokeRequest"]) => unwrap(await client.POST("/api/v1/access/revoke", { body })),
  accessOffboard: async (body: Schemas["OffboardRequest"]) => unwrap(await client.POST("/api/v1/access/offboard", { body })),
};
