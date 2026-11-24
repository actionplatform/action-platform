import { headers } from "next/headers";
import { NewTokenForm } from "@/features/account";
import { publicOrigin } from "@/lib/origin";
import type { Scope, ScopeInfo } from "@/lib/permissions";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export const dynamic = "force-dynamic";

export default async function NewTokenPage() {
  const { org } = await requireOrg();
  const [rows, access] = await Promise.all([v1.organizations(), v1.access()]);
  const organizations = await Promise.all(
    rows.map(async (o) => ({
      id: o.id,
      name: o.name,
      role: o.role_label ?? o.role ?? "member",
      grantable: o.grantable_scopes as Scope[],
      projects: (await v1.projects(o.id)).map((p) => ({ id: p.id, name: p.name, apps: p.apps.map((a) => ({ id: a.id, name: a.name })) })),
    })),
  );

  return <NewTokenForm organizations={organizations} scopes={access.scopes as ScopeInfo[]} activeOrganizationId={org.id} server={publicOrigin(await headers())} />;
}
