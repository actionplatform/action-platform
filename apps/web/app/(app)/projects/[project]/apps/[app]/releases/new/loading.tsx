import { PanelSkeleton, SkeletonStage } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <SkeletonStage>
      <div className="space-y-4">
        <div className="h-4 w-20 animate-pulse rounded bg-surface-hover" />
        <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]"><PanelSkeleton rows={6} /><PanelSkeleton rows={4} /></div>
      </div>
    </SkeletonStage>
  );
}
