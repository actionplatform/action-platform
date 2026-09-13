import { SkeletonStage } from "@/components/ui/skeleton";

function Block({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-lg bg-surface ${className}`} />;
}

export default function Loading() {
  return (
    <SkeletonStage label="Loading app">
      <Block className="h-4 w-56" />
      <Block className="mt-4 h-[34px] w-72" />
      <Block className="mt-2 h-4 w-80" />
      <div className="mt-6 h-11 border-b border-border" />
      <div className="mt-5 grid grid-cols-1 gap-3.5 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }).map((_, i) => <Block key={i} className="h-[104px]" />)}</div>
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(340px,1fr)]">
        <div className="space-y-4"><Block className="h-44" /><Block className="h-64" /><Block className="h-56" /></div>
        <div className="space-y-4"><Block className="h-64" /><Block className="h-44" /><Block className="h-56" /></div>
      </div>
    </SkeletonStage>
  );
}
