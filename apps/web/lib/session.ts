import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { getAuth } from "./auth";
import { activeOrg, type Org } from "./orgs";
import { setupStatus } from "./setup";

export async function getSession() {
  return (await getAuth()).api.getSession({ headers: await headers() });
}

// Signed in, or off to setup / login.
export async function requireSession() {
  const status = await setupStatus();
  if (!status.complete) redirect("/setup");

  const session = await getSession();
  if (!session) redirect("/login");

  return session;
}

// Signed in with an organization to work in; without one, create it first.
export async function requireOrg(): Promise<{ session: Awaited<ReturnType<typeof requireSession>>; org: Org }> {
  const session = await requireSession();
  const org = await activeOrg(session);
  if (!org) redirect("/orgs/new");

  return { session, org };
}
