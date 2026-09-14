import { headers } from "next/headers";
import { publicOrigin } from "@/lib/origin";
import { redirect } from "next/navigation";
import { oauthApps } from "@/lib/oauth";
import { getSession } from "@/lib/session";
import { setupStatus } from "@/lib/setup";
import { SetupWizard } from "./wizard";

type Search = { org?: string; connected?: string; oauth_error?: string; github_app?: string };

export default async function SetupPage({ searchParams }: { searchParams: Promise<Search> }) {
  const status = await setupStatus();
  if (status.complete) redirect("/login");
  const query = await searchParams;

  const h = await headers();
  const origin = publicOrigin(h);

  const initialStep = !status.dbOk ? 1 : !status.hasUser ? 2 : query.org ? 4 : 3;
  const none = { configured: false, slug: null as string | null };
  const apps = (await getSession()) && status.hasOrg ? await oauthApps() : { github: none, gitlab: none, bitbucket: none };

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <SetupWizard
        initialStep={initialStep}
        dbError={status.error}
        initialOrgId={query.org ?? null}
        oauth={{ configured: { github: apps.github.configured, gitlab: apps.gitlab.configured, bitbucket: apps.bitbucket.configured }, origin, connected: query.connected ?? null, error: query.oauth_error ?? null, githubApp: apps.github.slug ?? null }}
      />
    </div>
  );
}
