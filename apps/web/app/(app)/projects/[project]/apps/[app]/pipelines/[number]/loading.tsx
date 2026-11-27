import { SkeletonStage, TableSkeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return <SkeletonStage><TableSkeleton rows={8} columns={4} /></SkeletonStage>;
}
