import { redirect } from "next/navigation";
import { requireOrg } from "@/lib/session";
import { AccessSection } from "../../settings/access-section";

export const dynamic = "force-dynamic";

export default async function TeamAccessPage() {
  const { session } = await requireOrg();
  if (!session.grants["org.manage"]) redirect("/organization/members");
  return <AccessSection />;
}
