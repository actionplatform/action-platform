import { PluginSection } from "@/components/layout/plugin-section";

export const dynamic = "force-dynamic";

export default async function DeployPage() {
  return (
    <>
      <p className="mb-5 text-sm text-secondary">Where the code goes: the clouds and servers the organization deploys to, and the accounts they use.</p>
      <PluginSection groups={["deploy"]} title="Targets" description="Each target is a plugin; connect its account in its options." empty="No deploy plugin is installed. An instance owner adds them in Admin → Plugins." />
    </>
  );
}
