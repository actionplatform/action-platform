import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { loadApp } from "@/features/projects/load";
import { ReleaseCard } from "@/features/releases";

export default async function NewReleasePage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const back = `/projects/${view.projectId}/apps/${view.appId}/releases`;
  return (
    <div className="space-y-4">
      <Link href={back} className="inline-flex items-center gap-1.5 text-[13px] text-secondary hover:text-foreground"><ArrowLeft className="size-3.5" strokeWidth={1.75} /> Releases</Link>
      <ReleaseCard view={view} />
    </div>
  );
}
