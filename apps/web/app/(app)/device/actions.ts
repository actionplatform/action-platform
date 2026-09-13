"use server";

import { deviceRequest, type Grant, setDeviceGrant } from "@/lib/api-tokens";
import { orgsOf, roleOf } from "@/lib/orgs";
import { DEFAULT_SCOPES, grantableScopes, parseScopes, ROLE_INFO, type Scope } from "@/lib/permissions";
import { appsOf, projectsOf } from "@/lib/projects";
import { failed, type Result } from "@/lib/result";
import { requireOrg, requireSession } from "@/lib/session";

export type Choice = { id: string; name: string };
export type OrgChoice = Choice & { role: string; grantable: Scope[] };
export type DeviceView = { grant: Grant; clientId: string | null; organizations: OrgChoice[] };

export async function inspectDevice(userCode: string): Promise<Result<DeviceView>> {
  try {
    const { session, org } = await requireOrg();
    const request = await deviceRequest(userCode.trim().toUpperCase());
    if (!request || request.status !== "pending") return { ok: false, error: "invalid or expired code" };
    const organizations = await Promise.all(
      (await orgsOf(session.user.id)).map(async (o) => {
        const role = await roleOf(session.user.id, o.id);
        return { id: o.id, name: o.name, role: role ? ROLE_INFO[role]?.label ?? role : "member", grantable: grantableScopes(role) };
      }),
    );
    const grant = { ...request.grant, scope: request.grant.scope.length ? request.grant.scope : DEFAULT_SCOPES };
    if (!grant.organizationId || !organizations.some((o) => o.id === grant.organizationId)) grant.organizationId = org.id;
    const allowed = organizations.find((o) => o.id === grant.organizationId)?.grantable ?? ["read"];
    grant.scope = grant.scope.filter((s) => allowed.includes(s));
    return { ok: true, data: { grant, clientId: request.clientId, organizations } };
  } catch (e) {
    return failed(e);
  }
}

export async function projectChoices(organizationId: string): Promise<Result<Choice[]>> {
  try {
    const session = await requireSession();
    if (!(await orgsOf(session.user.id)).some((o) => o.id === organizationId)) return { ok: false, error: "not a member of that organization" };
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

export async function chooseDeviceGrant(userCode: string, input: { scope: string[]; organizationId: string; projectId: string | null; appId: string | null }): Promise<Result<Grant>> {
  try {
    const session = await requireSession();
    if (!(await orgsOf(session.user.id)).some((o) => o.id === input.organizationId)) return { ok: false, error: "not a member of that organization" };
    const allowed = grantableScopes(await roleOf(session.user.id, input.organizationId));
    const chosen = parseScopes(input.scope.join(" ")).filter((s) => allowed.includes(s));
    const grant: Grant = { scope: chosen.includes("read") ? chosen : ["read", ...chosen], organizationId: input.organizationId, projectId: input.projectId || null, appId: input.projectId ? input.appId || null : null };
    if (!(await setDeviceGrant(userCode.trim().toUpperCase(), grant))) return { ok: false, error: "invalid or expired code" };
    return { ok: true, data: grant };
  } catch (e) {
    return failed(e);
  }
}
