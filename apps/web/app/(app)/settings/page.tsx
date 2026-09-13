import { headers } from "next/headers";
import { ConnectHosts } from "@/components/connect-hosts";
import { PageHeader } from "@/components/layout/page";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE, api } from "@/lib/api";
import { hostAccess } from "@/lib/host-access";
import { appFor, isConfigured } from "@/lib/oauth";
import { invitationsOf, membersOf, roleOf } from "@/lib/orgs";
import { publicOrigin } from "@/lib/origin";
import { can } from "@/lib/permissions";
import { requireOrg } from "@/lib/session";
import { hostsOf } from "@/lib/source-hosts";
import { gitAuthorOf } from "@/lib/org-settings";
import { ApiCard } from "./api-card";
import { GitflowCard } from "./gitflow-card";
import { IdentityCard } from "./identity-card";
import { MembersPanel } from "./members-panel";
import { RolesCard } from "./roles-card";
import { SourceHosts } from "./source-hosts";

const DOCS_URL = "https://github.com/actionplatform/action-platform/blob/master/docs/use_api.md";

export default async function SettingsPage({ searchParams }: { searchParams: Promise<{ connected?: string; oauth_error?: string; github_app?: string }> }) {
  const { session, org } = await requireOrg();
  const [members, invitations, role, hosts, query, author] = await Promise.all([membersOf(org.id), invitationsOf(org.id), roleOf(session.user.id, org.id), hostsOf(org.id), searchParams, gitAuthorOf(org.id)]);
  const canManage = can(role, "org.manage");
  const githubSlug = appFor("github")?.slug ?? null;
  const access = Object.fromEntries(await Promise.all(hosts.filter((h) => h.kind !== "generic").map(async (h) => [h.id, await hostAccess(org.id, h.id, githubSlug)] as const)));
  const origin = publicOrigin(await headers());
  const connected = { github: [] as string[], gitlab: [] as string[], bitbucket: [] as string[] };
  for (const host of hosts) if (host.authKind === "oauth" && host.login && host.kind in connected) connected[host.kind as keyof typeof connected].push(host.login);

  let version: string | null = null;
  let rules: { kinds: string[]; protected: string[]; types: string[] } | null = null;
  try {
    [version, rules] = await Promise.all([api.version().then((v) => v.version), api.gitflowRules()]);
  } catch {}

  return (
    <>
      <PageHeader title="Settings" description="Manage workspace connections, roles and platform configuration." />
      <div className="space-y-5">
        <MembersPanel
          org={{ name: org.name, slug: org.slug }}
          members={members.map((m) => ({ id: m.id, userId: m.userId, name: m.name, email: m.email, role: m.role }))}
          invitations={invitations.map((i) => ({ id: i.id, email: i.email, role: i.role, inviter: i.inviter, expiresAt: i.expiresAt.toISOString() }))}
          me={session.user.id}
          canManage={canManage}
          origin={origin}
        />

        <Card>
          <CardHeader><CardTitle>Connect a code host</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {query.oauth_error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{query.oauth_error}</div>}
            {query.connected && <div className="text-sm text-secondary">Connected {query.connected}.</div>}
            {query.github_app && <div className="text-sm text-secondary">GitHub App <code className="font-mono">{query.github_app}</code> created. Install it, then connect.</div>}
            <ConnectHosts
              configured={{ github: isConfigured("github"), gitlab: isConfigured("gitlab"), bitbucket: isConfigured("bitbucket") }}
              connected={connected}
              origin={origin}
              orgId={org.id}
              returnTo="/settings"
              githubApp={githubSlug}
            />
          </CardContent>
        </Card>

        <SourceHosts hosts={hosts} access={access} canManage={canManage} />

        <IdentityCard author={author} canManage={canManage} />
        <RolesCard />
        <ApiCard baseUrl={API_BASE} version={version} docsUrl={DOCS_URL} />
        <GitflowCard rules={rules} />
      </div>
    </>
  );
}
