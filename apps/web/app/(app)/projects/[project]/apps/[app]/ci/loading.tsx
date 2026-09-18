import { PanelSkeleton, SkeletonStage } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <SkeletonStage>
      <div className="space-y-4"><PanelSkeleton rows={2} /><PanelSkeleton rows={6} /></div>
    </SkeletonStage>
  );
}
