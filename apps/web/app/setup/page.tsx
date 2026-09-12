import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { isConfigured } from "@/lib/oauth";
import { setupStatus } from "@/lib/setup";
import { SetupWizard } from "./wizard";

type Search = { org?: string; connected?: string; oauth_error?: string };

export default async function SetupPage({ searchParams }: { searchParams: Promise<Search> }) {
  const status = await setupStatus();
  if (status.complete) redirect("/login");
  const query = await searchParams;

  const h = await headers();
  const origin = `${h.get("x-forwarded-proto") ?? "http"}://${h.get("x-forwarded-host") ?? h.get("host")}`;

  // Back from a provider during setup: land on the hosts step for the org
  // named in the return URL.
  const initialStep = !status.dbOk ? 1 : !status.hasUser ? 2 : query.org ? 4 : 3;

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <SetupWizard
        initialStep={initialStep}
        dbError={status.error}
        initialOrgId={query.org ?? null}
        oauth={{ configured: { github: isConfigured("github"), gitlab: isConfigured("gitlab"), bitbucket: isConfigured("bitbucket") }, origin, connected: query.connected ?? null, error: query.oauth_error ?? null }}
      />
    </div>
  );
}
