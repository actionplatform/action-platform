import { type HostRow, v1 } from "./v1";

export { HOST_KINDS, type HostKind, type SourceHost } from "./source-host-kinds";
import type { HostKind, SourceHost } from "./source-host-kinds";

function host(row: HostRow, orgId: string): SourceHost {
  return { id: row.id, organizationId: orgId, kind: row.kind as HostKind, name: row.name, baseUrl: row.base_url ?? null, username: row.username ?? null, defaultOwner: row.default_owner ?? null, authKind: row.auth_kind as "token" | "oauth", login: row.login ?? null, createdAt: new Date(row.created_at) };
}

export async function hostsOf(orgId: string): Promise<SourceHost[]> {
  return (await v1.hosts()).map((h) => host(h, orgId));
}

export async function hostById(orgId: string, id: string): Promise<SourceHost | null> {
  return (await hostsOf(orgId)).find((h) => h.id === id) ?? null;
}
