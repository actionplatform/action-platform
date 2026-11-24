import { Lock } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel } from "@/components/ui/panel";
import { InstanceView } from "@/features/instance";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export const dynamic = "force-dynamic";

export default async function InstancePage() {
  const { session } = await requireOrg();
  if (session.role !== "owner") {
    return (
      <Panel>
        <EmptyState icon={Lock} title="Instance is for owners" text="Only an owner sees the health of workers, the queue and the email setup." />
      </Panel>
    );
  }

  let health: Awaited<ReturnType<typeof v1.instanceHealth>> | null = null;
  let error: string | null = null;
  try {
    health = await v1.instanceHealth();
  } catch (e) {
    error = e instanceof Error ? e.message : "The instance health could not be read.";
  }

  if (!health) {
    return <div className="rounded-md border border-status-bad/30 bg-status-bad/5 px-3 py-2 text-[13px] text-status-bad">{error}</div>;
  }

  return <InstanceView health={health} />;
}
