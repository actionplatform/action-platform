import { PanelSkeleton, SkeletonStage } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <SkeletonStage>
      <div className="space-y-4">
        <div className="h-4 w-24 animate-pulse rounded bg-surface-hover" />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,65fr)_minmax(300px,35fr)]"><PanelSkeleton rows={5} /><PanelSkeleton rows={4} /></div>
      </div>
    </SkeletonStage>
  );
}
