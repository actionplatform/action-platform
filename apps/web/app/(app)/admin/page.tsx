import { redirect } from "next/navigation";
import { PageHeader } from "@/components/layout/page";
import { PageTabs, pickTab, type PageTab } from "@/components/layout/page-tabs";
import { PluginSection } from "@/components/layout/plugin-section";
import { requireOrg } from "@/lib/session";
import { InstanceSection } from "../settings/instance-section";

export const dynamic = "force-dynamic";

export default async function AdminPage({ searchParams }: { searchParams: Promise<{ tab?: string }> }) {
  const { session } = await requireOrg();
  const tabs: PageTab[] = [];
  if (session.role === "owner") tabs.push({ id: "instance", label: "Instance" });
  if (session.grants["org.manage"]) tabs.push({ id: "plugins", label: "Plugins" });
  if (tabs.length === 0) redirect("/dashboard");
  const tab = pickTab(tabs, (await searchParams).tab);

  return (
    <>
      <PageHeader title="Admin" description="The platform itself: its health, its workers and every plugin it runs." />
      {tabs.length > 1 && <PageTabs label="Admin" tabs={tabs} active={tab} />}
      {tab === "instance" ? <InstanceSection /> : <PluginSection groups={["ci", "deploy", "observability", "notifications", "access", "other"]} title="Installed plugins" description="Every plugin this instance runs; most also show up under Connect." empty="The platform runs no plugins." />}
    </>
  );
}
