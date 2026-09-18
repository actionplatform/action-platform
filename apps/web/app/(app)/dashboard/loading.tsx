import { PanelSkeleton, SkeletonStage } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <SkeletonStage>
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-[84px] animate-pulse rounded-lg border border-border bg-surface" />)}</div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]"><PanelSkeleton rows={8} /><PanelSkeleton rows={4} /></div>
      </div>
    </SkeletonStage>
  );
}
