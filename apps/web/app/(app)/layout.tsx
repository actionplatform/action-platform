import type { ReactNode } from "react";
import { PageTransition } from "@/components/layout/page-transition";
import { ScopeProvider } from "@/components/layout/scope";
import { Sidebar } from "@/components/layout/sidebar";
import { api } from "@/lib/api";
import { orgsOf } from "@/lib/orgs";
import { requireOrg } from "@/lib/session";

export default async function AppLayout({ children }: { children: ReactNode }) {
  const { session, org } = await requireOrg();
  const orgs = await orgsOf(session.user.id);

  let version = "—";
  try {
    version = (await api.version()).version;
  } catch {}

  return (
    <ScopeProvider>
      <div className="min-h-screen bg-background">
        <Sidebar version={version} user={{ name: session.user.name, email: session.user.email }} org={org} orgs={orgs} />
        <main className="min-h-screen lg:ml-[272px]">
          <div className="w-full px-4 py-6 md:px-8 md:py-10 xl:px-12 xl:pt-[42px] xl:pb-16"><PageTransition>{children}</PageTransition></div>
        </main>
      </div>
    </ScopeProvider>
  );
}
