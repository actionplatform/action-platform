"use client";

import { ExternalLink, GitPullRequest, X } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

export function OpenedBanner({ number, url, branch, base }: { number: number; url: string | null; branch: string; base: string }) {
  const router = useRouter();
  const pathname = usePathname();
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-foreground bg-surface px-4 py-3 sm:flex-row sm:items-center">
      <GitPullRequest className="size-5 shrink-0" strokeWidth={1.75} />
      <div className="min-w-0 flex-1 text-sm">
        <div className="font-medium">Pull request #{number} opened from <span className="font-mono">{branch}</span> into <span className="font-mono">{base}</span></div>
        <div className="text-[13px] text-secondary">The changes are not on <span className="font-mono">{base}</span> yet. Review and merge the pull request on the code host; the next sync picks it up and the platform updates the release, branch and activity here.</div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {url && <a href={url} target="_blank" rel="noreferrer"><Button>Review and merge <ExternalLink className="size-3.5" strokeWidth={1.75} /></Button></a>}
        <button type="button" aria-label="Dismiss" onClick={() => router.replace(pathname)} className="flex size-8 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground"><X className="size-4" strokeWidth={1.75} /></button>
      </div>
    </div>
  );
}
