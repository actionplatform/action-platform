import type { ReactNode } from "react";
import { PageHeader } from "@/components/layout/page";

export default function SettingsLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <PageHeader title="Settings" description="The organization itself: name, commit identity, git-flow rules, the Git accounts it works with." />
      {children}
    </>
  );
}
