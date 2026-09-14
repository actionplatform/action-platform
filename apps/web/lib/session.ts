import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { getAuth } from "./auth";
import { activeOrg, type Org } from "./orgs";
import { safePath } from "./safe-path";
import { setupStatus } from "./setup";

export async function getSession() {
  return (await getAuth()).api.getSession({ headers: await headers() });
}

export async function requireSession() {
  const status = await setupStatus();
  if (!status.complete) redirect("/setup");

  const session = await getSession();
  if (!session) redirect(await loginUrl());

  return session;
}

export async function requireOrg(): Promise<{ session: Awaited<ReturnType<typeof requireSession>>; org: Org }> {
  const session = await requireSession();
  const org = await activeOrg(session);
  if (!org) redirect("/orgs/new");

  return { session, org };
}

async function loginUrl(): Promise<string> {
  const path = (await headers()).get("x-request-path");
  const safe = safePath(path, "/projects");
  const next = safe !== "/projects" && !safe.startsWith("/login") ? `?next=${encodeURIComponent(safe)}` : "";
  return `/login${next}`;
}
