import { PanelSkeleton, SkeletonStage, TableSkeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return <SkeletonStage><div className="space-y-4"><PanelSkeleton rows={2} /><TableSkeleton rows={8} columns={4} /></div></SkeletonStage>;
}
