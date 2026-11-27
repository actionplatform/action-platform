import { ciActivityOf } from "@/lib/ci";
import { requireOrg } from "@/lib/session";
import { CiActivityView } from "@/features/ci";

export const dynamic = "force-dynamic";

export default async function CiActivityPage() {
  await requireOrg();
  return <CiActivityView hosts={await ciActivityOf()} />;
}
