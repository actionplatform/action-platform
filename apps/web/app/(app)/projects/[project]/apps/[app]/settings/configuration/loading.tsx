import { PanelSkeleton, SkeletonStage } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <SkeletonStage>
      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <div className="space-y-4"><PanelSkeleton rows={5} /><PanelSkeleton rows={4} /></div>
        <PanelSkeleton rows={6} />
      </div>
    </SkeletonStage>
  );
}
