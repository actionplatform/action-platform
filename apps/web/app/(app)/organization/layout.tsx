import type { ReactNode } from "react";
import { PageHeader } from "@/components/layout/page";
import { SubNav } from "@/components/layout/sub-nav";
import { ORGANIZATION_PAGES } from "@/components/layout/nav";

export default function OrganizationLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <PageHeader title="Organization" description="Who is in it and what is signed in as them." />
      <SubNav label="Organization" pages={ORGANIZATION_PAGES} />
      {children}
    </>
  );
}
