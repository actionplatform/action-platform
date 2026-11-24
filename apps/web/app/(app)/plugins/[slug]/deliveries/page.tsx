import { notFound } from "next/navigation";
import { PageHeader } from "@/components/layout/page";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";
import { DeliveriesTable } from "@/features/plugins";

export const dynamic = "force-dynamic";

export default async function PluginDeliveriesPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const { session } = await requireOrg();
  if (!session.grants["org.manage"]) notFound();
  const catalog = await v1.plugins().catch(() => ({ plugins: [] }));
  const plugin = catalog.plugins.find((p) => p.slug === slug);
  if (!plugin || !plugin.events) notFound();
  const { deliveries } = await v1.pluginDeliveries(slug);

  return (
    <>
      <PageHeader title={`${plugin.name || plugin.slug} deliveries`} description="The latest events the plugin was handed for this organization, where each went and whether it arrived. A failed send is retried with backoff before it shows as failed." />
      <DeliveriesTable rows={deliveries} />
    </>
  );
}
