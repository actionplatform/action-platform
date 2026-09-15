import { CardGridSkeleton, SkeletonStage } from "@/components/ui/skeleton";

export default function Loading() {
  return <SkeletonStage label="Loading teams"><CardGridSkeleton /></SkeletonStage>;
}
