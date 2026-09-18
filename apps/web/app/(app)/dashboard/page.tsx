import { dashboardOf } from "@/lib/insights";
import { requireOrg } from "@/lib/session";
import { DashboardView } from "@/features/insights";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const { org } = await requireOrg();
  const data = await dashboardOf();
  return (
    <div className="space-y-4">
      <header><h1 className="text-[17px] font-semibold">{org.name}</h1><p className="text-[13px] text-secondary">Today across the organization.</p></header>
      <DashboardView data={data} />
    </div>
  );
}
