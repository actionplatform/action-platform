import { client, type Schemas, unwrap } from "@/lib/api";

export const serviceAccess = {
  accessAudit: async (service?: string) => unwrap(await client.GET("/api/v1/access/audit", { params: { query: { service } } })),
  accessWho: async (query: { person?: string; service?: string }) => unwrap(await client.GET("/api/v1/access/grants", { params: { query } })),
  accessSync: async (body: Schemas["app__schemas__service_access__SyncRequest"]) => unwrap(await client.POST("/api/v1/access/syncs", { body })),
  accessGrant: async ({ person, ...body }: { person: string } & Schemas["PersonGrant"]) =>
    unwrap(await client.POST("/api/v1/access/people/{person}/grants", { params: { path: { person } }, body })),
  accessRevoke: async ({ person, service, resource, apply }: { person: string; service: string; resource: string; apply?: boolean }) =>
    unwrap(await client.DELETE("/api/v1/access/people/{person}/grants/{service}/{resource}", { params: { path: { person, service, resource }, query: { apply } } })),
  accessOffboard: async ({ person, apply, remove_from_platform }: { person: string; apply?: boolean; remove_from_platform?: boolean }) =>
    unwrap(await client.DELETE("/api/v1/access/people/{person}", { params: { path: { person }, query: { apply, remove_from_platform } } })),
};
