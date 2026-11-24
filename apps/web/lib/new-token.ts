import { parseScopes, type Scope } from "./permissions";

export type NewToken = { name: string; scope: Scope[]; organizationId: string; projectId: string | null; appId: string | null };

export function tokenRequest(input: NewToken): { name: string; scope: string; organization_id: string; project_id: string | null; app_id: string | null } {
  const everywhere = input.organizationId === "*";
  const projectId = everywhere ? null : input.projectId || null;
  return { name: input.name.trim(), scope: parseScopes(input.scope.join(" ")).join(" ") || "read", organization_id: input.organizationId, project_id: projectId, app_id: projectId ? input.appId || null : null };
}
