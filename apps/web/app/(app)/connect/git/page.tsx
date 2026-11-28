import { Download } from "lucide-react";
import { headers } from "next/headers";
import Link from "next/link";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { hostAccess } from "@/lib/host-access";
import { oauthApps } from "@/lib/oauth";
import { publicOrigin } from "@/lib/origin";
import { requireOrg } from "@/lib/session";
import { hostsOf } from "@/lib/source-hosts";
import { ConnectHosts, SourceHosts } from "@/features/integrations";

export const dynamic = "force-dynamic";

type Query = { connected?: string; oauth_error?: string; github_app?: string };

export default async function GitPage({ searchParams }: { searchParams: Promise<Query> }) {
  const { session, org } = await requireOrg();
  const query = await searchParams;
  const canManage = !!session.grants["org.manage"];
  const [hosts, apps] = await Promise.all([hostsOf(org.id), oauthApps()]);
  const access = Object.fromEntries(await Promise.all(hosts.filter((h) => h.kind !== "generic").map(async (h) => [h.id, await hostAccess(org.id, h.id)] as const)));
  const origin = publicOrigin(await headers());
  const connected = { github: [] as string[], gitlab: [] as string[], bitbucket: [] as string[] };
  for (const host of hosts) if (host.authKind === "oauth" && host.login && host.kind in connected) connected[host.kind as keyof typeof connected].push(host.login);

  return (
    <>
      <p className="mb-5 text-sm text-secondary">Where the code lives: the GitHub, GitLab and Bitbucket accounts the organization clones, pushes and releases with.</p>
      <div className="space-y-5">
        <Panel>
          <PanelHeader title="Connect" description="Sign an account in, or install the GitHub App on another organization." />
          <div className="space-y-3 p-4">
            {query.connected && <div className="text-sm text-secondary">Connected {query.connected}.</div>}
            {query.github_app && <div className="text-sm text-secondary">GitHub App <code className="font-mono">{query.github_app}</code> created. Install it, then connect.</div>}
            <ConnectHosts
              configured={{ github: apps.github.configured, gitlab: apps.gitlab.configured, bitbucket: apps.bitbucket.configured }}
              connected={connected}
              origin={origin}
              orgId={org.id}
              returnTo="/connect/git"
              githubApp={apps.github.slug ?? null}
              githubAppKey={!apps.github.configured || !!apps.github.has_app_key}
              error={query.oauth_error ?? null}
            />
          </div>
        </Panel>
        <SourceHosts hosts={hosts} access={access} canManage={canManage} />
        {canManage && connected.github.length > 0 && (
          <Link href="/import" className="flex items-center gap-3 rounded-lg border border-border px-4 py-3 text-sm transition-colors hover:border-border-hover hover:bg-surface-hover">
            <Download className="size-4 text-secondary" strokeWidth={1.75} />
            <span><span className="font-medium">Import from GitHub</span> <span className="text-secondary">— bring the repositories, teams, people and projects in.</span></span>
          </Link>
        )}
      </div>
    </>
  );
}
