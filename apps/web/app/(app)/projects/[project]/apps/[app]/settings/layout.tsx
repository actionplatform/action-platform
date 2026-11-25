import type { ReactNode } from "react";
import { SubNav } from "@/components/layout/sub-nav";
import { APP_SETTINGS_PAGES, appPath } from "@/lib/app-routes";

export default async function AppSettingsLayout({ params, children }: { params: Promise<{ project: string; app: string }>; children: ReactNode }) {
  const { project, app } = await params;
  return (
    <>
      <SubNav label="App settings" pages={APP_SETTINGS_PAGES.map(({ tab, label, exact }) => ({ href: appPath(project, app, tab), label, exact }))} />
      {children}
    </>
  );
}
