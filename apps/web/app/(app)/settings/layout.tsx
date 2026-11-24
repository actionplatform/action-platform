import type { ReactNode } from "react";
import { PageHeader } from "@/components/layout/page";
import { SubNav } from "@/components/layout/sub-nav";
import { SETTINGS_PAGES, subNavPages } from "@/components/layout/nav";

export default function SettingsLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <PageHeader title="Settings" description="The organization itself: name, commit identity, git-flow rules, the Git accounts it works with." />
      <SubNav label="Settings" pages={subNavPages(SETTINGS_PAGES)} />
      {children}
    </>
  );
}
