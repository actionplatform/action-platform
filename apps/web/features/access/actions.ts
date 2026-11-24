"use server";

import { revalidatePath } from "next/cache";
import { failed, type Result } from "@/lib/result";
import { requireOrg } from "@/lib/session";
import { type AccessPlan, type AccessWho, v1 } from "@/lib/v1";

export type Operation =
  | { kind: "sync"; service?: string; reimport?: boolean }
  | { kind: "grant"; person: string; service: string; resource: string; level: string; account?: string }
  | { kind: "revoke"; person: string; service: string; resource: string }
  | { kind: "offboard"; person: string; removeFromPlatform?: boolean };

async function manager(): Promise<string | null> {
  const { session } = await requireOrg();
  return session.grants["org.manage"] ? null : "Only org.manage can manage service access.";
}

const clean = (v: string | undefined) => v?.trim() || undefined;

export async function lookup(query: { person?: string; service?: string }): Promise<Result<AccessWho>> {
  const denied = await manager();
  if (denied) return { ok: false, error: denied };
  const person = clean(query.person);
  const service = clean(query.service);
  if (!person && !service) return { ok: false, error: "Enter a person's email or choose a service." };
  try {
    return { ok: true, data: await v1.accessWho({ person, service }) };
  } catch (e) {
    return failed(e);
  }
}

export async function runOperation(op: Operation, apply: boolean): Promise<Result<AccessPlan>> {
  const denied = await manager();
  if (denied) return { ok: false, error: denied };
  try {
    let plan: AccessPlan;
    switch (op.kind) {
      case "sync":
        plan = await v1.accessSync({ service: clean(op.service) ?? null, apply, reimport: !!op.reimport });
        break;
      case "grant":
        if (!clean(op.person) || !clean(op.service) || !clean(op.resource) || !clean(op.level)) return { ok: false, error: "Person, service, resource and level are required." };
        plan = await v1.accessGrant({ person: op.person.trim(), service: op.service.trim(), resource: op.resource.trim(), level: op.level.trim(), account: clean(op.account) ?? null, apply });
        break;
      case "revoke":
        if (!clean(op.person) || !clean(op.service) || !clean(op.resource)) return { ok: false, error: "Person, service and resource are required." };
        plan = await v1.accessRevoke({ person: op.person.trim(), service: op.service.trim(), resource: op.resource.trim(), apply });
        break;
      case "offboard":
        if (!clean(op.person)) return { ok: false, error: "Enter the person's email." };
        plan = await v1.accessOffboard({ person: op.person.trim(), apply, remove_from_platform: !!op.removeFromPlatform });
        break;
    }
    if (apply) revalidatePath("/settings/access");
    return { ok: true, data: plan };
  } catch (e) {
    return failed(e);
  }
}
