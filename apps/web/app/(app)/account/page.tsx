import { PageHeader } from "@/components/layout/page";
import { tokensOfUser } from "@/lib/api-tokens";
import { requireSession } from "@/lib/session";
import { sessionsOf } from "@/lib/sessions";
import { v1 } from "@/lib/v1";
import { SessionsCard } from "./sessions-card";
import { TokensCard } from "./tokens-card";

export default async function AccountPage() {
  await requireSession();
  const [tokens, sessions, access] = await Promise.all([tokensOfUser(), sessionsOf(), v1.access()]);
  const now = Date.now();

  return (
    <>
      <PageHeader title="Connected apps" description="Everything signed in as you: browsers, and the CLI and MCP servers holding an API token. Revoke what you do not recognise." />
      <div className="space-y-6">
        <TokensCard tokens={tokens} now={now} scopes={access.scopes} />
        <SessionsCard sessions={sessions} now={now} />
      </div>
    </>
  );
}
