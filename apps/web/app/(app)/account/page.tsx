import { PageHeader } from "@/components/layout/page";
import { tokensOfUser } from "@/lib/api-tokens";
import { requireSession } from "@/lib/session";
import { sessionsOf } from "@/lib/sessions";
import { SessionsCard } from "./sessions-card";
import { TokensCard } from "./tokens-card";

export default async function AccountPage() {
  await requireSession();
  const [tokens, sessions] = await Promise.all([tokensOfUser(), sessionsOf()]);
  const now = Date.now();

  return (
    <>
      <PageHeader title="Connected apps" description="Everything signed in as you: browsers, and the CLI and MCP servers holding an API token. Revoke what you do not recognise." />
      <div className="space-y-6">
        <TokensCard tokens={tokens} now={now} />
        <SessionsCard sessions={sessions} now={now} />
      </div>
    </>
  );
}
