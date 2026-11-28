import { Panel, PanelHeader } from "@/components/ui/panel";
import { PluginCards } from "@/features/plugins";
import { type PluginGroup, pluginCards } from "@/lib/plugin-cards";

export async function PluginSection({ groups, title, description, empty }: { groups: PluginGroup[]; title: string; description: string; empty: string }) {
  const { plugins, canManage } = await pluginCards(groups);
  return (
    <Panel>
      <PanelHeader title={title} description={description} />
      <div className="p-4">{plugins.length === 0 ? <p className="text-sm text-secondary">{empty}</p> : <PluginCards plugins={plugins} canManage={canManage} />}</div>
    </Panel>
  );
}
