export function TemplateCardSkeleton() {
  return (
    <div aria-hidden className="flex min-h-[164px] flex-col rounded-[9px] border border-border bg-surface p-4">
      <div className="flex items-start gap-3">
        <div className="size-[42px] animate-pulse rounded-lg bg-surface-hover" />
        <div className="flex-1 space-y-2 pt-1">
          <div className="h-4 w-1/3 animate-pulse rounded bg-surface-hover" />
          <div className="h-3 w-3/4 animate-pulse rounded bg-surface-hover" />
        </div>
      </div>
      <div className="mt-auto border-t border-border-subtle pt-3.5"><div className="h-3 w-1/2 animate-pulse rounded bg-surface-hover" /></div>
    </div>
  );
}
