import { PageHeader } from "@/components/layout/page";
import { PageTabs, pickTab, type PageTab } from "@/components/layout/page-tabs";
import { requireOrg } from "@/lib/session";
import { AccessSection } from "./access-section";
import { GeneralSection, type GeneralQuery } from "./general-section";
import { InstanceSection } from "./instance-section";

export const dynamic = "force-dynamic";

export default async function SettingsPage({ searchParams }: { searchParams: Promise<GeneralQuery & { tab?: string }> }) {
  const { session } = await requireOrg();
  const query = await searchParams;
  const tabs: PageTab[] = [{ id: "general", label: "General" }];
  if (session.grants["org.manage"]) tabs.push({ id: "access", label: "Access" });
  if (session.role === "owner") tabs.push({ id: "instance", label: "Instance" });
  const tab = pickTab(tabs, query.tab);

  return (
    <>
      <PageHeader title="Settings" description="The organization itself: name, commit identity, git-flow rules, the Git accounts it works with." />
      {tabs.length > 1 && <PageTabs label="Settings" tabs={tabs} active={tab} />}
      {tab === "access" ? <AccessSection /> : tab === "instance" ? <InstanceSection /> : <GeneralSection query={query} />}
    </>
  );
}
