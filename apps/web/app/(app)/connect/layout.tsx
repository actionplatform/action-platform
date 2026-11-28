import type { ReactNode } from "react";
import { PageHeader } from "@/components/layout/page";
import { SubNav } from "@/components/layout/sub-nav";
import { CONNECT_PAGES, subNavPages } from "@/components/layout/nav";

export default function ConnectLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <PageHeader title="Connect" description="What the organization works with outside the platform: code, CI, clouds, observability and notifications." shortDescription="Git, CI, Deploy, Observability, Notifications." />
      <SubNav label="Connect" pages={subNavPages(CONNECT_PAGES)} />
      {children}
    </>
  );
}
