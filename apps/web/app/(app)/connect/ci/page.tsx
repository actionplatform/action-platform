import { PageTabs, pickTab, type PageTab } from "@/components/layout/page-tabs";
import { PluginSection } from "@/components/layout/plugin-section";
import { ciActivityOf, ciHostsOf } from "@/lib/ci";
import { requireOrg } from "@/lib/session";
import { CiActivityView, CiHosts } from "@/features/ci";

export const dynamic = "force-dynamic";

const TABS: PageTab[] = [
  { id: "servers", label: "Servers" },
  { id: "activity", label: "Activity" },
];

export default async function CiPage({ searchParams }: { searchParams: Promise<{ tab?: string }> }) {
  const { session } = await requireOrg();
  const tab = pickTab(TABS, (await searchParams).tab);

  return (
    <>
      <p className="mb-5 text-sm text-secondary">Where the code is tested and built: the CI servers the organization connects, and what they ran.</p>
      <PageTabs label="CI" tabs={TABS} active={tab} />
      {tab === "activity" ? (
        <CiActivityView hosts={await ciActivityOf()} />
      ) : (
        <div className="space-y-5">
          <CiHosts hosts={await ciHostsOf()} canManage={!!session.grants["org.manage"]} />
          <PluginSection groups={["ci"]} title="CI plugins" description="The plugins that teach the platform a CI server." empty="No CI plugin is installed." />
        </div>
      )}
    </>
  );
}
