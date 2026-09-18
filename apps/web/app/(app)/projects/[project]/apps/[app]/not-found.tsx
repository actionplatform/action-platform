import Link from "next/link";
import { FolderX } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-[420px] flex-col items-center justify-center rounded-lg border border-dashed border-border px-6 text-center">
      <FolderX className="size-6 text-secondary" strokeWidth={1.5} />
      <h1 className="mt-4 text-[17px] font-semibold">Project not found</h1>
      <p className="mt-1 max-w-sm text-sm text-secondary">The project may have been removed or you may not have access to it.</p>
      <Link href="/projects" className="mt-6"><Button variant="outline">Back to projects</Button></Link>
    </div>
  );
}
