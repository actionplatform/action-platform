import { Block } from "@/components/ui/skeleton";
import { DashboardSkeleton } from "@/features/insights";

export default function Loading() {
  return (
    <div className="space-y-6 xl:space-y-7">
      <div aria-hidden><Block className="h-[42px] w-48" /><Block className="mt-2 h-5 w-64" /></div>
      <DashboardSkeleton />
    </div>
  );
}
