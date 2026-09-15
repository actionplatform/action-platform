import { AwsCard } from "@/features/integrations";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export const dynamic = "force-dynamic";

export default async function CloudPage() {
  const { session, org } = await requireOrg();
  const canManage = !!session.grants["org.manage"];
  const aws = canManage ? await v1.pluginOptions("aws-lambda").catch(() => null) : null;
  const proxyUrl = typeof aws?.options?.proxy_url === "string" ? aws.options.proxy_url : null;

  return (
    <div className="space-y-5">
      <AwsCard proxyUrl={proxyUrl} orgSlug={org.slug} canManage={canManage} />
    </div>
  );
}
