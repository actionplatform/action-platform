import { Download } from "lucide-react";
import { headers } from "next/headers";
import Link from "next/link";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { api } from "@/lib/api";
import { v1 } from "@/lib/v1";
import { hostAccess } from "@/lib/host-access";
import { oauthApps } from "@/lib/oauth";
import { gitAuthorOf } from "@/lib/org-settings";
import { publicOrigin } from "@/lib/origin";
import { requireOrg } from "@/lib/session";
import { hostsOf } from "@/lib/source-hosts";
import { ciHostsOf } from "@/lib/ci";
import { CiHosts } from "@/features/ci";
import { ConnectHosts, SourceHosts } from "@/features/integrations";
import { DeleteOrganizationCard, GitflowCard, IdentityCard } from "@/features/organization";

export const dynamic = "force-dynamic";

export default async function GeneralSettingsPage({ searchParams }: { searchParams: Promise<{ connected?: string; oauth_error?: string; github_app?: string }> }) {
  const { session, org } = await requireOrg();
  const canManage = !!session.grants["org.manage"];
  const [author, hosts, query, apps, ciHosts, projects] = await Promise.all([gitAuthorOf(), hostsOf(org.id), searchParams, oauthApps(), ciHostsOf(), v1.projects(org.id).catch(() => [])]);
  const access = Object.fromEntries(await Promise.all(hosts.filter((h) => h.kind !== "generic").map(async (h) => [h.id, await hostAccess(org.id, h.id)] as const)));
  const origin = publicOrigin(await headers());
  const connected = { github: [] as string[], gitlab: [] as string[], bitbucket: [] as string[] };
  for (const host of hosts) if (host.authKind === "oauth" && host.login && host.kind in connected) connected[host.kind as keyof typeof connected].push(host.login);

  let rules: { kinds: string[]; protected: string[]; types: string[] } | null = null;
  try {
    rules = await api.gitflowRules();
  } catch {}

  return (
    <div className="space-y-5">
      <Panel>
        <PanelHeader title="Organization" />
        <dl className="grid grid-cols-1 gap-4 p-4 text-sm sm:grid-cols-2">
          <div><dt className="text-xs text-secondary">Name</dt><dd className="mt-0.5 font-medium">{org.name}</dd></div>
          <div><dt className="text-xs text-secondary">Slug</dt><dd className="mt-0.5 font-mono">{org.slug}</dd></div>
          <div><dt className="text-xs text-secondary">Your role</dt><dd className="mt-0.5">{session.role}</dd></div>
        </dl>
      </Panel>
      <IdentityCard author={author} canManage={canManage} />
      <GitflowCard rules={rules} />
      <Panel>
        <PanelHeader title="Git" description="GitHub, GitLab, Bitbucket — the accounts the organization pushes and releases with." />
        <div className="space-y-3 p-4">
          {query.connected && <div className="text-sm text-secondary">Connected {query.connected}.</div>}
          {query.github_app && <div className="text-sm text-secondary">GitHub App <code className="font-mono">{query.github_app}</code> created. Install it, then connect.</div>}
          <ConnectHosts
            configured={{ github: apps.github.configured, gitlab: apps.gitlab.configured, bitbucket: apps.bitbucket.configured }}
            connected={connected}
            origin={origin}
            orgId={org.id}
            returnTo="/settings"
            githubApp={apps.github.slug ?? null}
            error={query.oauth_error ?? null}
          />
        </div>
      </Panel>
      <SourceHosts hosts={hosts} access={access} canManage={canManage} />
      <CiHosts hosts={ciHosts} canManage={canManage} />
      {canManage && connected.github.length > 0 && (
        <Link href="/import" className="flex items-center gap-3 rounded-lg border border-border px-4 py-3 text-sm transition-colors hover:border-border-hover hover:bg-surface-hover">
          <Download className="size-4 text-secondary" strokeWidth={1.75} />
          <span><span className="font-medium">Import from GitHub</span> <span className="text-secondary">— bring the repositories, teams, people and projects in.</span></span>
        </Link>
      )}
      <DeleteOrganizationCard slug={org.slug} name={org.name} isOwner={session.role === "owner"} projects={projects.length} apps={projects.reduce((n, p) => n + (p.apps?.length ?? 0), 0)} />
    </div>
  );
}
