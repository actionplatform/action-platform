import { headers } from "next/headers";
import { PluginSection } from "@/components/layout/plugin-section";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { publicOrigin } from "@/lib/origin";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";
import { ConnectServices } from "@/features/integrations";

export const dynamic = "force-dynamic";

export default async function ObservabilityPage() {
  const { session, org } = await requireOrg();
  const services = await v1.connections().catch(() => []);
  const origin = publicOrigin(await headers());

  return (
    <>
      <p className="mb-5 text-sm text-secondary">How the apps are running: the tools for monitoring, errors, metrics, logs, traces and profiles.</p>
      <div className="space-y-5">
        <Panel>
          <PanelHeader title="Accounts" description="Connect each tool once; the plugins that use it read this connection." />
          <div className="p-4">
            {services.length === 0 ? <p className="text-sm text-secondary">No observability tool can be connected yet.</p> : <ConnectServices rows={services} origin={origin} orgId={org.id} returnTo="/connect/observability" canManage={!!session.grants["org.manage"]} />}
          </div>
        </Panel>
        <PluginSection groups={["observability"]} title="Plugins" description="What each observability plugin does with its account." empty="No observability plugin is installed." />
      </div>
    </>
  );
}
