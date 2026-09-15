import { PanelSkeleton, SkeletonStage } from "@/components/ui/skeleton";

export default function Loading() {
  return <SkeletonStage label="Loading plugins"><PanelSkeleton /></SkeletonStage>;
}
