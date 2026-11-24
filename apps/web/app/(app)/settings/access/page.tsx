import { Panel } from "@/components/ui/panel";
import { EmptyState } from "@/components/ui/empty-state";
import { Lock } from "lucide-react";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";
import { AccessLookup, AccessOperations, ServiceAudits } from "@/features/access";

export const dynamic = "force-dynamic";

export default async function AccessPage() {
  const { session } = await requireOrg();
  if (!session.grants["org.manage"]) {
    return (
      <Panel>
        <EmptyState icon={Lock} title="Access needs org.manage" text="Only members who can manage the organization see and change service access." />
      </Panel>
    );
  }

  let audit: Awaited<ReturnType<typeof v1.accessAudit>> | null = null;
  let error: string | null = null;
  try {
    audit = await v1.accessAudit();
  } catch (e) {
    error = e instanceof Error ? e.message : "The audit could not be read.";
  }

  if (!audit) {
    return <div className="rounded-md border border-status-bad/30 bg-status-bad/5 px-3 py-2 text-[13px] text-status-bad">{error}</div>;
  }

  return (
    <div className="space-y-5">
      <ServiceAudits audit={audit} />
      {audit.services.length > 0 && (
        <>
          <AccessLookup services={audit.services.map((s) => s.service)} />
          <AccessOperations services={audit.services} />
        </>
      )}
    </div>
  );
}
