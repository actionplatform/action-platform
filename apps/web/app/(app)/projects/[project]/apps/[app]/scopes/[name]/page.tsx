import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { scopesOf } from "@/lib/scopes";
import { loadApp } from "@/features/projects/load";
import { ScopeForm } from "@/features/scopes";

export default async function EditScopePage({ params }: { params: Promise<{ project: string; app: string; name: string }> }) {
  const { project, app, name } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const base = `/projects/${view.projectId}/apps/${view.appId}`;
  const scopes = await scopesOf(view.projectId, view.appId);
  const scope = scopes.items.find((s) => s.name === decodeURIComponent(name));
  if (!scope) notFound();
  return (
    <div className="space-y-4">
      <Link href={`${base}/scopes`} className="inline-flex items-center gap-1.5 text-[13px] text-secondary hover:text-foreground"><ArrowLeft className="size-3.5" strokeWidth={1.75} /> Scopes</Link>
      <ScopeForm projectId={view.projectId} appId={view.appId} base={base} vocabulary={scopes} scope={scope} canEdit={!!view.can["app.configure"]} />
    </div>
  );
}
