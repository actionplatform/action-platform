import { headers } from "next/headers";
import { PageHeader } from "@/components/layout/page";
import { publicOrigin } from "@/lib/origin";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";
import { PluginCards, type PluginCardData } from "@/features/plugins";

export const dynamic = "force-dynamic";

function filled(url: string, issuer: string, organization: string): string {
  return url.replaceAll("{issuer}", encodeURIComponent(issuer)).replaceAll("{organization}", encodeURIComponent(organization));
}

async function pluginCards(canManage: boolean, issuer: string, organization: string): Promise<PluginCardData[]> {
  const catalog = await v1.plugins().catch(() => ({ plugins: [] }));
  return Promise.all(
    catalog.plugins.map(async (p) => {
      const options = (p.options ?? []).map((o) => ({ ...o, action_url: o.action_url ? filled(o.action_url, issuer, organization) : "" }));
      const values = canManage && options.length > 0 ? await v1.pluginOptions(p.slug).then((r) => r.options).catch(() => ({})) : {};
      return { slug: p.slug, name: p.name || p.slug, version: p.version, description: p.description, error: p.error ?? null, options, values: values as Record<string, unknown> };
    }),
  );
}

export default async function PluginsPage() {
  const { session, org } = await requireOrg();
  const canManage = !!session.grants["org.manage"];
  const plugins = await pluginCards(canManage, publicOrigin(await headers()), org.slug);

  return (
    <>
      <PageHeader title="Plugins" description="What the platform runs beyond the core: deploy targets, overlays, tools. Configure the ones that ask for it." />
      {plugins.length === 0 ? (
        <p className="text-sm text-secondary">The platform runs no plugins.</p>
      ) : (
        <PluginCards plugins={plugins} canManage={canManage} />
      )}
    </>
  );
}
