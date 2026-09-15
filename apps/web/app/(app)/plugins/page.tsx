import { PageHeader } from "@/components/layout/page";
import { type Grants } from "@/lib/permissions";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";
import { PluginsCatalog, type PluginItem } from "./plugins-catalog";
import { PluginsErrorState } from "./plugins-states";

export const dynamic = "force-dynamic";

export default async function PluginsPage() {
  const { session } = await requireOrg();
  const grants = session.grants as Grants;

  let data: { plugins: PluginItem[]; index: string; hosted: boolean; restart_pending: string[] } | null = null;
  try {
    data = await v1.plugins();
  } catch {}

  if (!data) {
    return (
      <>
        <PageHeader title="Plugins" description="Deploy targets, overlays, tools and release strategies." />
        <PluginsErrorState />
      </>
    );
  }

  return <PluginsCatalog plugins={data.plugins} index={data.index} hosted={data.hosted} restartPending={data.restart_pending} canManage={!!grants["org.manage"]} />;
}
