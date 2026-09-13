import { PageHeader } from "@/components/layout/page";
import { SkeletonStage } from "@/components/ui/skeleton";
import { TemplateCardSkeleton } from "./template-card-skeleton";

export default function Loading() {
  return (
    <>
      <PageHeader title="Templates" description="Start faster with production-ready foundations for apps, libraries, documentation, plugins, and cloud services." />
      <SkeletonStage>
      <div className="mt-[26px] flex flex-col gap-3 md:flex-row">
        <div className="h-11 flex-1 animate-pulse rounded-lg bg-surface" />
        <div className="h-11 w-full animate-pulse rounded-lg bg-surface md:w-[204px]" />
        <div className="h-11 w-[86px] animate-pulse rounded-lg bg-surface" />
      </div>
      <div className="mt-4 flex gap-2">{Array.from({ length: 7 }).map((_, i) => <div key={i} className="h-[38px] w-20 animate-pulse rounded-[7px] bg-surface" />)}</div>
      <div className="mt-[22px] mb-3.5 h-4 w-32 animate-pulse rounded bg-surface" />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 9 }).map((_, i) => <TemplateCardSkeleton key={i} />)}
      </div>
      </SkeletonStage>
    </>
  );
}
