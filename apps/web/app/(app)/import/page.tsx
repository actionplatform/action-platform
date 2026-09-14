import { PageHeader } from "@/components/layout/page";
import { requireOrg } from "@/lib/session";
import { hostsOf } from "@/lib/source-hosts";
import { v1 } from "@/lib/v1";
import { ImportWizard } from "./import-wizard";

export const dynamic = "force-dynamic";

export default async function ImportPage() {
  const { session, org } = await requireOrg();
  const [hosts, catalog] = await Promise.all([hostsOf(org.id), v1.access()]);
  const canManage = !!session.grants["org.manage"];

  return (
    <>
      <PageHeader title="Import" description={`Bring a GitHub organization into ${org.name}: repositories become projects, teams become teams, people become members or invitations.`} />
      <ImportWizard
        hosts={hosts.map((h) => ({ id: h.id, kind: h.kind, name: h.name, login: h.login }))}
        roles={catalog.roles.filter((r) => r.id !== "owner").map((r) => ({ id: r.id, label: r.label }))}
        canManage={canManage}
      />
    </>
  );
}
