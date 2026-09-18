import { PanelSkeleton, SkeletonStage } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <SkeletonStage>
      <div className="space-y-4">
        <div className="h-4 w-24 animate-pulse rounded bg-surface-hover" />
        <PanelSkeleton rows={5} />
      </div>
    </SkeletonStage>
  );
}
