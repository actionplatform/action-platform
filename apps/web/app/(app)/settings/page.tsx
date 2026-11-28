import { PageHeader } from "@/components/layout/page";
import { PageTabs, pickTab, type PageTab } from "@/components/layout/page-tabs";
import { requireOrg } from "@/lib/session";
import { GeneralSection, GitRulesSection } from "./general-section";

export const dynamic = "force-dynamic";

const TABS: PageTab[] = [
  { id: "general", label: "General" },
  { id: "git-rules", label: "Git rules" },
];

export default async function SettingsPage({ searchParams }: { searchParams: Promise<{ tab?: string }> }) {
  await requireOrg();
  const tab = pickTab(TABS, (await searchParams).tab);

  return (
    <>
      <PageHeader title="Settings" description="The organization itself: its name, the identity commits are made with, and the git-flow rules." />
      <PageTabs label="Settings" tabs={TABS} active={tab} />
      {tab === "git-rules" ? <GitRulesSection /> : <GeneralSection />}
    </>
  );
}
