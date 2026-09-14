"use server";

import { revalidatePath } from "next/cache";
import { setActiveOrg } from "@/lib/orgs";
import { requireSession } from "@/lib/session";

export async function switchOrganization(orgId: string) {
  await requireSession();
  await setActiveOrg(orgId);
  revalidatePath("/", "layout");
}
