import type { ReactNode } from "react";
import { PageHeader } from "@/components/layout/page";
import { SubNav } from "@/components/layout/sub-nav";
import { INTEGRATIONS_PAGES, subNavPages } from "@/components/layout/nav";

export default function IntegrationsLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <PageHeader title="Integrations" description="What the organization connects to: GitHub, GitLab, Bitbucket, clouds." />
      <SubNav label="Integrations" pages={subNavPages(INTEGRATIONS_PAGES)} />
      {children}
    </>
  );
}
