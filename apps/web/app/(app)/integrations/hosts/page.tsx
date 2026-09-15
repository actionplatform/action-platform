import { Download } from "lucide-react";
import { headers } from "next/headers";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { hostAccess } from "@/lib/host-access";
import { oauthApps } from "@/lib/oauth";
import { publicOrigin } from "@/lib/origin";
import { requireOrg } from "@/lib/session";
import { hostsOf } from "@/lib/source-hosts";
import { ConnectHosts, SourceHosts } from "@/features/integrations";

export const dynamic = "force-dynamic";

export default async function CodeHostsPage({ searchParams }: { searchParams: Promise<{ connected?: string; oauth_error?: string; github_app?: string }> }) {
  const { session, org } = await requireOrg();
  const canManage = !!session.grants["org.manage"];
  const [hosts, query, apps] = await Promise.all([hostsOf(org.id), searchParams, oauthApps()]);
  const access = Object.fromEntries(await Promise.all(hosts.filter((h) => h.kind !== "generic").map(async (h) => [h.id, await hostAccess(org.id, h.id)] as const)));
  const origin = publicOrigin(await headers());
  const connected = { github: [] as string[], gitlab: [] as string[], bitbucket: [] as string[] };
  for (const host of hosts) if (host.authKind === "oauth" && host.login && host.kind in connected) connected[host.kind as keyof typeof connected].push(host.login);

  return (
    <div className="space-y-5">
      <Card className="rounded-[11px]">
        <header className="border-b border-border px-6 py-4"><h2 className="text-[18px] font-semibold">Git</h2><p className="mt-0.5 text-sm text-secondary">GitHub, GitLab, Bitbucket.</p></header>
        <div className="space-y-3 px-4 py-4 sm:px-6">
          {query.connected && <div className="text-sm text-secondary">Connected {query.connected}.</div>}
          {query.github_app && <div className="text-sm text-secondary">GitHub App <code className="font-mono">{query.github_app}</code> created. Install it, then connect.</div>}
          <ConnectHosts
            configured={{ github: apps.github.configured, gitlab: apps.gitlab.configured, bitbucket: apps.bitbucket.configured }}
            connected={connected}
            origin={origin}
            orgId={org.id}
            returnTo="/integrations/hosts"
            githubApp={apps.github.slug ?? null}
            error={query.oauth_error ?? null}
          />
        </div>
      </Card>
      <SourceHosts hosts={hosts} access={access} canManage={canManage} />
      {canManage && connected.github.length > 0 && (
        <Link href="/import" className="flex items-center gap-3 rounded-[11px] border border-border px-6 py-4 text-sm transition-colors hover:border-border-hover hover:bg-surface-hover">
          <Download className="size-4 text-secondary" strokeWidth={1.75} />
          <span><span className="font-medium">Import from GitHub</span> <span className="text-secondary">— bring the repositories, teams, people and projects in.</span></span>
        </Link>
      )}
    </div>
  );
}
