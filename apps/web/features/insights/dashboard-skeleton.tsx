import { PanelSkeleton } from "@/components/ui/skeleton";

export function DashboardSkeleton() {
  return (
    <div aria-busy data-testid="dashboard-skeleton" className="space-y-5 xl:space-y-6">
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => <div key={i} aria-hidden className="h-[136px] animate-pulse rounded-[10px] border border-border bg-surface" />)}
      </div>
      <PanelSkeleton rows={3} className="rounded-[10px]" />
      <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] xl:gap-6">
        <PanelSkeleton rows={6} className="rounded-[10px]" />
        <div className="space-y-5"><PanelSkeleton rows={2} className="rounded-[10px]" /><PanelSkeleton rows={2} className="rounded-[10px]" /></div>
      </div>
    </div>
  );
}
