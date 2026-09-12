"use server";

import { revalidatePath } from "next/cache";
import { isMember, setActiveOrg } from "@/lib/orgs";
import { requireSession } from "@/lib/session";

export async function switchOrganization(orgId: string) {
  const session = await requireSession();
  if (!(await isMember(session.user.id, orgId))) return;
  await setActiveOrg(orgId);
  revalidatePath("/", "layout");
}
