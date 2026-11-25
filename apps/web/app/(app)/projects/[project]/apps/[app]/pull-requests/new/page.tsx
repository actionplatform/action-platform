import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { appPath } from "@/lib/app-routes";
import { PullRequestCard } from "@/features/activity";
import { loadApp } from "@/features/projects/load";

export default async function NewPullRequestPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  return (
    <div className="space-y-4">
      <Link href={appPath(view.projectId, view.appId, "")} className="inline-flex items-center gap-1.5 text-[13px] text-secondary hover:text-foreground"><ArrowLeft className="size-3.5" strokeWidth={1.75} /> Overview</Link>
      <PullRequestCard view={view} />
    </div>
  );
}
