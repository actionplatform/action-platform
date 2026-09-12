import type { ReactNode } from "react";
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
  } catch {
    // API offline: the pages say so themselves.
  }

  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      <Sidebar version={version} user={{ name: session.user.name, email: session.user.email }} org={org} orgs={orgs} />
      <main className="flex-1 min-w-0 px-4 py-6 md:px-8 md:py-8">
        <div className="mx-auto max-w-6xl">{children}</div>
      </main>
    </div>
  );
}
