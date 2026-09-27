import { Activity } from "lucide-react";
import { PageHeader } from "@/components/layout/page";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel } from "@/components/ui/panel";
import { dashboardOf } from "@/lib/insights";
import { requireOrg } from "@/lib/session";
import { EventRow, grouped } from "@/features/insights";

export const dynamic = "force-dynamic";

export default async function ActivityPage() {
  const { org } = await requireOrg();
  const data = await dashboardOf();
  const groups = grouped(data.events);
  return (
    <>
      <PageHeader title="Activity" description={`Releases, deployments, CI runs and pull requests across ${org.name}.`} />
      <Panel>
        {groups.length === 0 ? (
          <EmptyState icon={Activity} title="Nothing yet" text="Releases, deployments, CI runs and pull requests land here as the apps sync." />
        ) : (
          <ul className="divide-y divide-border-subtle">{groups.map((g, i) => <EventRow key={`${g.event.kind}-${g.event.app_id}-${i}`} event={g.event} count={g.count} />)}</ul>
        )}
      </Panel>
    </>
  );
}
