import { PageHeader } from "@/components/layout/page";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE, api } from "@/lib/api";

export default async function SettingsPage() {
  let version: string | null = null;
  let rules: { kinds: string[]; protected: string[]; types: string[] } | null = null;
  try {
    [version, rules] = await Promise.all([api.version().then((v) => v.version), api.gitflowRules()]);
  } catch {
    // shown as offline below
  }

  return (
    <>
      <PageHeader title="Settings" />
      <div className="space-y-4">
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
