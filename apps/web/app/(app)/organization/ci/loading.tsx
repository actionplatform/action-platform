import { SkeletonStage, TableSkeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return <SkeletonStage><TableSkeleton rows={6} columns={3} /></SkeletonStage>;
}
