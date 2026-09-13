export const ROLES = ["owner", "admin", "deployer", "developer", "viewer"] as const;
export type Role = (typeof ROLES)[number];

export const PERMISSIONS = ["org.manage", "project.manage", "app.release", "app.configure", "app.flow", "app.sync"] as const;
export type Permission = (typeof PERMISSIONS)[number];

export const ROLE_INFO: Record<Role, { label: string; description: string }> = {
  owner: { label: "Owner", description: "Everything, including deleting the organization. At least one per organization." },
  admin: { label: "Admin", description: "Members, teams, code hosts, projects and every app action." },
  deployer: { label: "Deployer", description: "Cuts releases and edits configuration, plus everything a developer can do." },
  developer: { label: "Developer", description: "Branches, pull requests, commits and sync. No releases." },
  viewer: { label: "Viewer", description: "Read-only access to projects, apps, releases and activity." },
};

const GRANTS: Record<Role, Permission[]> = {
  owner: ["org.manage", "project.manage", "app.release", "app.configure", "app.flow", "app.sync"],
  admin: ["org.manage", "project.manage", "app.release", "app.configure", "app.flow", "app.sync"],
  deployer: ["app.release", "app.configure", "app.flow", "app.sync"],
  developer: ["app.configure", "app.flow", "app.sync"],
  viewer: [],
};

export const PERMISSION_INFO: Record<Permission, string> = {
  "org.manage": "Manage members, teams, code hosts and settings",
  "project.manage": "Create and delete projects, add and remove apps",
  "app.release": "Create releases",
  "app.configure": "Edit configuration, deploy target, services and commit",
  "app.flow": "Start branches, check out, push and open pull requests",
  "app.sync": "Sync workspaces with the code host",
};

export type Grants = Record<Permission, boolean>;

export function isRole(value: string): value is Role {
  return (ROLES as readonly string[]).includes(value);
}

export function normalizeRole(value: string | null): Role | null {
  if (!value) return null;
  if (value === "member") return "developer";
  return isRole(value) ? value : null;
}

export function can(role: string | null, permission: Permission): boolean {
  const r = normalizeRole(role);
  return !!r && GRANTS[r].includes(permission);
}

export function grantsOf(role: string | null): Grants {
  return Object.fromEntries(PERMISSIONS.map((p) => [p, can(role, p)])) as Grants;
}
