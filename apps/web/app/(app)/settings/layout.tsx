import type { ReactNode } from "react";
import { PageHeader } from "@/components/layout/page";
import { SettingsSubNav } from "./sub-nav";

export default function SettingsLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <PageHeader title="Settings" description="The organization: who is in it, what it connects to, how it releases." />
      <SettingsSubNav />
      {children}
    </>
  );
}
