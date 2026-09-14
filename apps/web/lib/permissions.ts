export const ROLES = ["owner", "admin", "deployer", "developer", "viewer"] as const;
export type Role = (typeof ROLES)[number];

export const PERMISSIONS = ["org.manage", "project.manage", "app.release", "app.configure", "app.flow", "app.sync"] as const;
export type Permission = (typeof PERMISSIONS)[number];

export const SCOPES = ["read", "write", "release", "admin"] as const;
export type Scope = (typeof SCOPES)[number];

export type Grants = Record<Permission, boolean>;

export function isRole(value: string): value is Role {
  return (ROLES as readonly string[]).includes(value);
}

export function isScope(value: string): value is Scope {
  return (SCOPES as readonly string[]).includes(value);
}

export function parseScopes(value: string | null | undefined): Scope[] {
  const seen = new Set<Scope>();
  for (const part of (value ?? "").split(/[\s,]+/)) if (isScope(part)) seen.add(part);
  return SCOPES.filter((s) => seen.has(s));
}

export type RoleInfo = { id: string; label: string; description: string; permissions: string[]; grantable_scopes: string[] };
export type ScopeInfo = { id: string; label: string; description: string; permissions: string[] };
export type AccessCatalog = { roles: RoleInfo[]; permissions: { id: string; description: string }[]; scopes: ScopeInfo[]; default_scopes: string[] };
