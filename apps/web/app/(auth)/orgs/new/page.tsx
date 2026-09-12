import { activeOrg } from "@/lib/orgs";
import { requireSession } from "@/lib/session";
import { OrgForm } from "./org-form";

export default async function NewOrgPage() {
  const session = await requireSession();
  const org = await activeOrg(session);
  const first = org === null;

  return <OrgForm first={first} />;
}

export const dynamic = "force-dynamic";
