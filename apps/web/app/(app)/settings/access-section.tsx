import { v1 } from "@/lib/v1";
import { AccessLookup, AccessOperations, ServiceAudits } from "@/features/access";

export async function AccessSection() {
  let audit: Awaited<ReturnType<typeof v1.accessAudit>> | null = null;
  let error: string | null = null;
  try {
    audit = await v1.accessAudit();
  } catch (e) {
    error = e instanceof Error ? e.message : "The audit could not be read.";
  }

  return (
    <div className="space-y-5">
      {audit ? (
        <>
          <ServiceAudits audit={audit} />
          {audit.services.length > 0 && (
            <>
              <AccessLookup services={audit.services.map((s) => s.service)} />
              <AccessOperations services={audit.services} />
            </>
          )}
        </>
      ) : (
        <div className="rounded-md border border-status-bad/30 bg-status-bad/5 px-3 py-2 text-[13px] text-status-bad">{error}</div>
      )}
    </div>
  );
}
