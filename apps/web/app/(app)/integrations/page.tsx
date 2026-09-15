import { Download } from "lucide-react";
import { headers } from "next/headers";
import Link from "next/link";
import { PageHeader } from "@/components/layout/page";
import { hostAccess } from "@/lib/host-access";
import { oauthApps } from "@/lib/oauth";
import { publicOrigin } from "@/lib/origin";
import { requireOrg } from "@/lib/session";
import { hostsOf } from "@/lib/source-hosts";
import { v1 } from "@/lib/v1";
import { ConnectHosts, PluginCards, type PluginCardData, SourceHosts } from "@/features/integrations";

export const dynamic = "force-dynamic";

async function pluginCards(canManage: boolean): Promise<PluginCardData[]> {
  const catalog = await v1.plugins().catch(() => ({ plugins: [] }));
  return Promise.all(
    catalog.plugins.map(async (p) => {
      const options = p.options ?? [];
      const values = canManage && options.length > 0 ? await v1.pluginOptions(p.slug).then((r) => r.options).catch(() => ({})) : {};
      return { slug: p.slug, name: p.name || p.slug, version: p.version, description: p.description, error: p.error ?? null, options, values: values as Record<string, unknown> };
    }),
  );
}

export default async function IntegrationsPage({ searchParams }: { searchParams: Promise<{ connected?: string; oauth_error?: string; github_app?: string }> }) {
  const { session, org } = await requireOrg();
  const canManage = !!session.grants["org.manage"];
  const [hosts, query, apps, plugins] = await Promise.all([hostsOf(org.id), searchParams, oauthApps(), pluginCards(canManage)]);
  const access = Object.fromEntries(await Promise.all(hosts.filter((h) => h.kind !== "generic").map(async (h) => [h.id, await hostAccess(org.id, h.id)] as const)));
  const origin = publicOrigin(await headers());
  const connected = { github: [] as string[], gitlab: [] as string[], bitbucket: [] as string[] };
  for (const host of hosts) if (host.authKind === "oauth" && host.login && host.kind in connected) connected[host.kind as keyof typeof connected].push(host.login);

  return (
    <>
      <PageHeader title="Integrations" description="What the organization connects to: GitHub, GitLab, Bitbucket, and the plugins the platform runs." />
      <div className="space-y-5">
        {query.connected && <div className="text-sm text-secondary">Connected {query.connected}.</div>}
        {query.github_app && <div className="text-sm text-secondary">GitHub App <code className="font-mono">{query.github_app}</code> created. Install it, then connect.</div>}
        <ConnectHosts
          configured={{ github: apps.github.configured, gitlab: apps.gitlab.configured, bitbucket: apps.bitbucket.configured }}
          connected={connected}
          origin={origin}
          orgId={org.id}
          returnTo="/integrations"
          githubApp={apps.github.slug ?? null}
          error={query.oauth_error ?? null}
          extra={<PluginCards plugins={plugins} canManage={canManage} />}
        />
        <SourceHosts hosts={hosts} access={access} canManage={canManage} />
        {canManage && connected.github.length > 0 && (
          <Link href="/import" className="flex items-center gap-3 rounded-[11px] border border-border px-6 py-4 text-sm transition-colors hover:border-border-hover hover:bg-surface-hover">
            <Download className="size-4 text-secondary" strokeWidth={1.75} />
            <span><span className="font-medium">Import from GitHub</span> <span className="text-secondary">— bring the repositories, teams, people and projects in.</span></span>
          </Link>
        )}
      </div>
    </>
  );
}
