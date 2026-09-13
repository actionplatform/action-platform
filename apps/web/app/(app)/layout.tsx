import type { ReactNode } from "react";
import { PageTransition } from "@/components/layout/page-transition";
import { ScopeProvider } from "@/components/layout/scope";
import { BottomNav } from "@/components/layout/bottom-nav";
import { Sidebar } from "@/components/layout/sidebar";
import { api } from "@/lib/api";
import { WEB_VERSION } from "@/lib/sentry";
import { orgsOf } from "@/lib/orgs";
import { requireOrg } from "@/lib/session";

export default async function AppLayout({ children }: { children: ReactNode }) {
  const { session, org } = await requireOrg();
  const orgs = await orgsOf(session.user.id);

  let versions = { web: WEB_VERSION, api: "—", lib: "—" };
  try {
    const v = await api.version();
    versions = { ...versions, api: v.api, lib: v.version };
  } catch {}

  return (
    <ScopeProvider>
      <div className="min-h-screen bg-background">
        <Sidebar versions={versions} user={{ name: session.user.name, email: session.user.email }} org={org} orgs={orgs} />
        <main className="min-h-screen pb-[calc(88px+env(safe-area-inset-bottom))] md:ml-[280px] md:pb-0">
          <div className="w-full px-5 py-6 md:px-7 md:py-8 xl:px-8 xl:pt-9 xl:pb-16"><PageTransition>{children}</PageTransition></div>
        </main>
        <BottomNav />
      </div>
    </ScopeProvider>
  );
}
