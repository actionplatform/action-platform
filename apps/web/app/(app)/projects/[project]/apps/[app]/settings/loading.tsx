import { PanelSkeleton, SkeletonStage } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <SkeletonStage>
      <div className="space-y-4"><PanelSkeleton rows={4} /><PanelSkeleton rows={5} /><PanelSkeleton rows={4} /></div>
    </SkeletonStage>
  );
}
