import { ArrowRight } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { buttonVariants } from "@/components/ui/button";
import { type Dashboard, dashboardOf } from "@/lib/insights";
import { failed } from "@/lib/result";
import { requireOrg } from "@/lib/session";
import { DashboardError, DashboardView } from "@/features/insights";

export const dynamic = "force-dynamic";

function DashboardHeader({ greeting }: { greeting?: ReactNode }) {
  return (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <h1 className="text-[34px] font-semibold leading-[42px]">Dashboard</h1>
        {greeting && <p className="mt-1 truncate text-[17px] text-secondary">{greeting}</p>}
      </div>
      <Link href="/projects" className={buttonVariants({ variant: "outline", size: "lg", className: "shrink-0 self-start" })}>
        View projects
        <ArrowRight className="size-4" strokeWidth={1.75} aria-hidden />
      </Link>
    </header>
  );
}

export default async function DashboardPage() {
  const { session, org } = await requireOrg();
  const first = session.user.name.trim().split(/\s+/)[0] || session.user.name;
  let data: Dashboard | null = null;
  let error: string | null = null;
  try {
    data = await dashboardOf();
  } catch (e) {
    error = failed(e).error;
  }
  return (
    <div className="space-y-6 xl:space-y-7">
      <DashboardHeader greeting={`Welcome back, ${first}`} />
      {data ? <DashboardView key={org.id} data={data} orgId={org.id} /> : <DashboardError reason={error ?? ""} />}
    </div>
  );
}
