import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { dashboardOf } from "@/lib/insights";
import { requireOrg } from "@/lib/session";
import { DashboardView } from "@/features/insights";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const { session, org } = await requireOrg();
  const data = await dashboardOf();
  const first = session.user.name.trim().split(/\s+/)[0] || session.user.name;
  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h1 className="truncate text-[28px] font-semibold leading-9">Welcome back, {first}</h1>
          <p className="mt-1 truncate text-[15px] text-secondary">{org.name} overview</p>
        </div>
        <Link href="/projects" className={buttonVariants({ variant: "outline", className: "shrink-0 self-start sm:self-auto" })}>
          View projects
          <ArrowRight className="size-4" strokeWidth={1.75} aria-hidden />
        </Link>
      </header>
      <DashboardView data={data} />
    </div>
  );
}
