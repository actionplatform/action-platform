import { PageHeader } from "@/components/layout/page";
import { api } from "@/lib/api";
import { requireOrg } from "@/lib/session";
import { PluginsCatalog, type PluginItem } from "./plugins-catalog";
import { PluginsErrorState } from "./plugins-states";

export const dynamic = "force-dynamic";

export default async function PluginsPage() {
  await requireOrg();

  let data: { plugins: PluginItem[]; index: string } | null = null;
  try {
    data = await api.plugins();
  } catch {}

  if (!data) {
    return (
      <>
        <PageHeader title="Plugins" description="Extensions for the CLI and the MCP server: deploy targets, overlays, tools, release strategies." />
        <PluginsErrorState />
      </>
    );
  }

  return <PluginsCatalog plugins={data.plugins} index={data.index} />;
}
