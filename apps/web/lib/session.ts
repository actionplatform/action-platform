import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { type Session, sessionCookie, sessionFromCookie } from "./auth";
import type { Org } from "./orgs";
import { safePath } from "./safe-path";
import { setupStatus } from "./setup";

export type { Session };

export async function getSession(): Promise<Session | null> {
  return sessionFromCookie(await sessionCookie());
}

export async function requireSession(): Promise<Session> {
  const status = await setupStatus();
  if (!status.complete) redirect("/setup");

  const session = await getSession();
  if (!session) redirect(await loginUrl());

  return session;
}

export async function requireOrg(): Promise<{ session: Session; org: Org }> {
  const session = await requireSession();
  const org = session.organization;
  if (!org) redirect("/orgs/new");

  return { session, org: { id: org.id, name: org.name, slug: org.slug } };
}

async function loginUrl(): Promise<string> {
  const path = (await headers()).get("x-request-path");
  const safe = safePath(path, "/projects");
  const next = safe !== "/projects" && !safe.startsWith("/login") ? `?next=${encodeURIComponent(safe)}` : "";
  return `/login${next}`;
}
