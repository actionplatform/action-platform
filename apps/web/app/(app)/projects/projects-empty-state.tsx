import { FolderGit2, SearchX } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export function ProjectsEmptyState({ onCreate }: { onCreate?: () => void }) {
  return (
    <div className="flex min-h-[420px] flex-col items-center justify-center rounded-[9px] border border-dashed border-border px-6 text-center">
      <FolderGit2 className="size-6 text-secondary" strokeWidth={1.5} />
      <h2 className="mt-4 text-[17px] font-semibold">No projects yet</h2>
      <p className="mt-1 max-w-sm text-sm text-secondary">Create your first project to start deploying applications.</p>
      <div className="mt-6 flex flex-col gap-2 sm:flex-row">
        {onCreate && <Button size="lg" onClick={onCreate}>Create project</Button>}
        <Link href="/templates"><Button size="lg" variant="outline" className="w-full">Browse templates</Button></Link>
      </div>
    </div>
  );
}

export function ProjectsNoResults({ query, onClear }: { query: string; onClear: () => void }) {
  return (
    <div className="flex min-h-[320px] flex-col items-center justify-center rounded-[9px] border border-dashed border-border px-6 text-center">
      <SearchX className="size-6 text-secondary" strokeWidth={1.5} />
      <h2 className="mt-4 text-[17px] font-semibold">No projects found</h2>
      <p className="mt-1 text-sm text-secondary">No projects match &ldquo;{query}&rdquo;.</p>
      <Button variant="outline" className="mt-6" onClick={onClear}>Clear search</Button>
    </div>
  );
}
