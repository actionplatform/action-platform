import { PageHeader } from "@/components/layout/page";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Td, Th } from "@/components/ui/table";
import { API_BASE, api } from "@/lib/api";
import { membersOf } from "@/lib/orgs";
import { requireOrg } from "@/lib/session";
import { headers } from "next/headers";
import { ConnectHosts } from "@/components/connect-hosts";
import { appFor, isConfigured } from "@/lib/oauth";
import { hostsOf } from "@/lib/source-hosts";
import { SourceHosts } from "./source-hosts";

export default async function SettingsPage({ searchParams }: { searchParams: Promise<{ connected?: string; oauth_error?: string; github_app?: string }> }) {
  const { org } = await requireOrg();
  const [members, hosts, query] = await Promise.all([membersOf(org.id), hostsOf(org.id), searchParams]);
  const h = await headers();
  const origin = `${h.get("x-forwarded-proto") ?? "http"}://${h.get("x-forwarded-host") ?? h.get("host")}`;
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
        <Card>
          <CardHeader><CardTitle>Organization</CardTitle><Badge className="font-mono">{org.slug}</Badge></CardHeader>
          <Table>
            <thead><tr><Th>member</Th><Th>email</Th><Th>role</Th></tr></thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.id}><Td>{m.name}</Td><Td className="text-secondary">{m.email}</Td><Td><Badge>{m.role}</Badge></Td></tr>
              ))}
            </tbody>
          </Table>
        </Card>

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
              returnTo="/settings"
              githubApp={appFor("github")?.slug ?? null}
            />
          </CardContent>
        </Card>

        <SourceHosts hosts={hosts} />

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
