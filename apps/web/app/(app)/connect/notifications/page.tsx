import { PluginSection } from "@/components/layout/plugin-section";

export const dynamic = "force-dynamic";

export default async function NotificationsPage() {
  return (
    <>
      <p className="mb-5 text-sm text-secondary">Who is told when something happens: the channels releases, deploys and failures go to.</p>
      <PluginSection groups={["notifications"]} title="Channels" description="Each channel is a plugin; set where it sends in its options." empty="No notification plugin is installed." />
    </>
  );
}
