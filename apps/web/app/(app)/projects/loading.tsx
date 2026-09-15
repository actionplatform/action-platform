import { PageHeader } from "@/components/layout/page";
import { SkeletonStage } from "@/components/ui/skeleton";
import { ProjectCardSkeleton } from "@/features/projects";

export default function Loading() {
  return (
    <>
      <PageHeader title="Projects" description="Manage your projects and the apps that ship together." />
      <SkeletonStage>
      <div className="mt-7 mb-6 flex flex-col gap-3 md:flex-row">
        <div className="h-11 w-full max-w-[640px] animate-pulse rounded-lg bg-surface" />
        <div className="h-11 w-full animate-pulse rounded-lg bg-surface md:ml-auto md:w-48" />
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => <ProjectCardSkeleton key={i} />)}
      </div>
      </SkeletonStage>
    </>
  );
}
