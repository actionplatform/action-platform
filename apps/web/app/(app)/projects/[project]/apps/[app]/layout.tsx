import type { ReactNode } from "react";
import { AppScopeMarker } from "@/components/layout/scope";
import { AppHeader } from "@/features/projects";
import { AppErrorState } from "@/features/projects";
import { loadApp } from "@/features/projects";

export const dynamic = "force-dynamic";

export default async function AppLayout({ params, children }: { params: Promise<{ project: string; app: string }>; children: ReactNode }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);

  if (!loaded.ok) return <AppErrorState name={loaded.name} projectId={loaded.projectId} reason={loaded.reason} />;

  const { view } = loaded;
  return (
    <>
      <AppScopeMarker projectId={view.projectId} projectName={view.projectName} appId={view.appId} appName={view.name} />
      <AppHeader view={view} />
      <div className="mt-6">{children}</div>
    </>
  );
}
