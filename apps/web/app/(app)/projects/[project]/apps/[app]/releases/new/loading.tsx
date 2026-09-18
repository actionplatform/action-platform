import { PanelSkeleton, SkeletonStage } from "@/components/ui/skeleton";

export default function Loading() {
  return <SkeletonStage><PanelSkeleton rows={6} /></SkeletonStage>;
}
