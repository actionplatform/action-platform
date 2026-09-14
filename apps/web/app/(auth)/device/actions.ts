"use server";

import { approveDevice, denyDevice, deviceRequest, type Grant } from "@/lib/api-tokens";
import { v1 } from "@/lib/v1";
import type { Scope, ScopeInfo } from "@/lib/permissions";
import { appsOf, projectsOf } from "@/lib/projects";
import { isAuthError } from "@/lib/auth-api";
import { failed, type Result } from "@/lib/result";
import { requireOrg, requireSession } from "@/lib/session";

export type Choice = { id: string; name: string };
export type OrgChoice = Choice & { role: string; grantable: Scope[] };
export type DeviceView = { grant: Grant; requested: Scope[]; clientId: string | null; expiresAt: number; organizations: OrgChoice[]; scopes: ScopeInfo[] };

export async function inspectDevice(userCode: string): Promise<Result<DeviceView>> {
  try {
    const { session, org } = await requireOrg();
    const request = await deviceRequest(userCode.trim().toUpperCase());
    if (!request) return { ok: false, error: "invalid code" };
    if (request.status === "expired") return { ok: false, error: "expired" };
    if (request.status !== "pending") return { ok: false, error: `this code was already ${request.status}` };
    const [rows, access] = await Promise.all([v1.organizations(), v1.access()]);
    const organizations = rows.map((o) => ({ id: o.id, name: o.name, role: o.role_label ?? "member", grantable: o.grantable_scopes as Scope[] }));
    const grant = { ...request.grant, scope: request.grant.scope.length ? request.grant.scope : (access.default_scopes as Scope[]) };
    if (!grant.organizationId) grant.organizationId = "*";
    if (grant.organizationId !== "*" && !organizations.some((o) => o.id === grant.organizationId)) grant.organizationId = org.id;
    const requested = grant.scope;
    const allowed = grant.organizationId === "*" ? [...new Set(organizations.flatMap((o) => o.grantable))] : organizations.find((o) => o.id === grant.organizationId)?.grantable ?? ["read"];
    grant.scope = grant.scope.filter((s) => allowed.includes(s));
    return { ok: true, data: { grant, requested, clientId: request.clientId, expiresAt: request.expiresAt.getTime(), organizations, scopes: access.scopes as ScopeInfo[] } };
  } catch (e) {
    return failed(e);
  }
}

export async function projectChoices(organizationId: string): Promise<Result<Choice[]>> {
  try {
    const session = await requireSession();
    if (!session.organizations.some((o) => o.id === organizationId)) return { ok: false, error: "not a member of that organization" };
    return { ok: true, data: (await projectsOf(organizationId)).map((p) => ({ id: p.id, name: p.name })) };
  } catch (e) {
    return failed(e);
  }
}

export async function appChoices(projectId: string): Promise<Result<Choice[]>> {
  try {
    await requireSession();
    return { ok: true, data: (await appsOf(projectId)).map((a) => ({ id: a.id, name: a.name })) };
  } catch (e) {
    return failed(e);
  }
}

export async function approveDeviceRequest(userCode: string, input: { scope: string[]; organizationId: string; projectId: string | null; appId: string | null }): Promise<Result<null>> {
  try {
    await requireSession();
    const everywhere = input.organizationId === "*";
    const grant: Grant = { scope: input.scope as Scope[], organizationId: everywhere ? null : input.organizationId, projectId: everywhere ? null : input.projectId || null, appId: !everywhere && input.projectId ? input.appId || null : null };
    await approveDevice(userCode.trim().toUpperCase(), grant);
    return { ok: true, data: null };
  } catch (e) {
    if (isAuthError(e) && e.code === "expired") return { ok: false, error: "expired" };
    return failed(e);
  }
}

export async function denyDeviceRequest(userCode: string): Promise<Result<null>> {
  try {
    await requireSession();
    await denyDevice(userCode.trim().toUpperCase());
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}
