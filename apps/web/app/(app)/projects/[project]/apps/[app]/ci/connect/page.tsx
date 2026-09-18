import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { ciHostsOf, ciOf } from "@/lib/ci";
import { ConnectCi } from "@/features/ci";
import { loadApp } from "@/features/projects/load";

export default async function ConnectCiPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const back = `/projects/${view.projectId}/apps/${view.appId}/ci`;
  const [state, hosts] = await Promise.all([ciOf(view.projectId, view.appId), ciHostsOf()]);
  return (
    <div className="space-y-4">
      <Link href={back} className="inline-flex items-center gap-1.5 text-[13px] text-secondary hover:text-foreground"><ArrowLeft className="size-3.5" strokeWidth={1.75} /> CI</Link>
      <ConnectCi projectId={view.projectId} appId={view.appId} state={state} hosts={hosts} sourceKind={view.sourceKind} backHref={back} />
    </div>
  );
}
