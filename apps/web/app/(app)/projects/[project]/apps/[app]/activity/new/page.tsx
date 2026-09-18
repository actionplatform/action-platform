import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { PullRequestCard } from "@/features/activity";
import { loadApp } from "@/features/projects/load";

export default async function NewPullRequestPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  return (
    <div className="space-y-4">
      <Link href={`/projects/${view.projectId}/apps/${view.appId}/activity`} className="inline-flex items-center gap-1.5 text-[13px] text-secondary hover:text-foreground"><ArrowLeft className="size-3.5" strokeWidth={1.75} /> Activity</Link>
      <PullRequestCard view={view} />
    </div>
  );
}
