import { PageHeader } from "@/components/layout/page";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE, api } from "@/lib/api";
import { invitationsOf, membersOf, roleOf } from "@/lib/orgs";
import { MembersPanel } from "./members-panel";
import { can, PERMISSION_INFO, PERMISSIONS, ROLE_INFO, ROLES } from "@/lib/permissions";
import { requireOrg } from "@/lib/session";
import { headers } from "next/headers";
import { publicOrigin } from "@/lib/origin";
import { ConnectHosts } from "@/components/connect-hosts";
import { appFor, isConfigured } from "@/lib/oauth";
import { hostsOf } from "@/lib/source-hosts";
import { githubAccess } from "@/lib/github-access";
import { SourceHosts } from "./source-hosts";

export default async function SettingsPage({ searchParams }: { searchParams: Promise<{ connected?: string; oauth_error?: string; github_app?: string }> }) {
  const { session, org } = await requireOrg();
  const [members, invitations, role, hosts, query] = await Promise.all([membersOf(org.id), invitationsOf(org.id), roleOf(session.user.id, org.id), hostsOf(org.id), searchParams]);
  const canManage = can(role, "org.manage");
  const githubSlug = appFor("github")?.slug ?? null;
  const access = Object.fromEntries(await Promise.all(hosts.filter((h) => h.kind === "github").map(async (h) => [h.id, await githubAccess(org.id, h.id, githubSlug)] as const)));
  const h = await headers();
  const origin = publicOrigin(h);
  const connected = { github: [] as string[], gitlab: [] as string[], bitbucket: [] as string[] };
  for (const host of hosts) if (host.authKind === "oauth" && host.login && host.kind in connected) connected[host.kind as keyof typeof connected].push(host.login);
  let version: string | null = null;
  let rules: { kinds: string[]; protected: string[]; types: string[] } | null = null;
  try {
    [version, rules] = await Promise.all([api.version().then((v) => v.version), api.gitflowRules()]);
  } catch {
  }

  return (
    <>
      <PageHeader title="Settings" description={org.name} />
      <div className="space-y-4">
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
              githubApp={appFor("github")?.slug ?? null}
            />
          </CardContent>
        </Card>

        <SourceHosts hosts={hosts} access={access} />

        <Card>
          <CardHeader><CardTitle>Roles and permissions</CardTitle><Badge>{ROLES.length} roles</Badge></CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground">
                  <th className="px-4 py-2 font-medium">Permission</th>
                  {ROLES.map((r) => <th key={r} className="px-3 py-2 text-center font-medium" title={ROLE_INFO[r].description}>{ROLE_INFO[r].label}</th>)}
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle border-t border-border-subtle">
                {PERMISSIONS.map((p) => (
                  <tr key={p}>
                    <td className="px-4 py-2.5"><div className="font-mono text-xs">{p}</div><div className="text-[13px] text-secondary">{PERMISSION_INFO[p]}</div></td>
                    {ROLES.map((r) => <td key={r} className="px-3 py-2.5 text-center">{can(r, p) ? <span aria-label="allowed" className="inline-block size-2 rounded-full bg-foreground" /> : <span aria-label="not allowed" className="inline-block size-2 rounded-full border border-border" />}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card>
          <CardHeader><CardTitle>API</CardTitle><Badge tone={version ? "ok" : "bad"}>{version ? `v${version}` : "offline"}</Badge></CardHeader>
          <CardContent className="text-sm space-y-1">
            <div><span className="text-muted-foreground w-24 inline-block">base url</span><code className="font-mono text-xs">{API_BASE}</code></div>
            <div className="text-muted-foreground text-xs">Set <code className="font-mono">AP_API</code> to point the app at another host.</div>
          </CardContent>
        </Card>

        {rules && (
          <Card>
            <CardHeader><CardTitle>Git-flow rules</CardTitle></CardHeader>
            <CardContent className="text-sm space-y-3">
              <div><div className="text-muted-foreground text-xs mb-1">branch kinds</div><div className="flex flex-wrap gap-1">{rules.kinds.map((k) => <Badge key={k} className="font-mono">{k}/</Badge>)}</div></div>
              <div><div className="text-muted-foreground text-xs mb-1">protected</div><div className="flex flex-wrap gap-1">{rules.protected.map((k) => <Badge key={k} className="font-mono">{k}</Badge>)}</div></div>
              <div><div className="text-muted-foreground text-xs mb-1">commit types</div><div className="flex flex-wrap gap-1">{rules.types.map((k) => <Badge key={k} className="font-mono">{k}:</Badge>)}</div></div>
            </CardContent>
          </Card>
        )}
      </div>
    </>
  );
}
