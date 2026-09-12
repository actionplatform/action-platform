import type { ReactNode } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { api } from "@/lib/api";
import { requireSession } from "@/lib/session";

export default async function AppLayout({ children }: { children: ReactNode }) {
  const session = await requireSession();

  let version = "—";
  try {
    version = (await api.version()).version;
  } catch {
    // API offline: the pages say so themselves.
  }

  return (
    <div className="min-h-screen flex">
      <Sidebar version={version} user={{ name: session.user.name, email: session.user.email }} />
      <main className="flex-1 min-w-0 p-8 max-w-6xl">{children}</main>
    </div>
  );
}
