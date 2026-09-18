export function ProjectCardSkeleton() {
  return (
    <div aria-hidden className="flex h-[180px] flex-col rounded-lg border border-border bg-surface px-6 py-[22px]">
      <div className="flex items-start justify-between">
        <div className="size-12 animate-pulse rounded-lg bg-surface-hover" />
        <div className="flex gap-2"><div className="size-8 animate-pulse rounded-md bg-surface-hover" /><div className="size-8 animate-pulse rounded-md bg-surface-hover" /></div>
      </div>
      <div className="mt-4 h-4 w-2/5 animate-pulse rounded bg-surface-hover" />
      <div className="mt-2 h-3 w-1/4 animate-pulse rounded bg-surface-hover" />
      <div className="mt-auto border-t border-border-subtle pt-4"><div className="h-3 w-3/5 animate-pulse rounded bg-surface-hover" /></div>
    </div>
  );
}
