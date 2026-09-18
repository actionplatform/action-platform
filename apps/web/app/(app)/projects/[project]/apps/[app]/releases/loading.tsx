import { SkeletonStage, TableSkeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return <SkeletonStage><TableSkeleton rows={10} columns={6} /></SkeletonStage>;
}
