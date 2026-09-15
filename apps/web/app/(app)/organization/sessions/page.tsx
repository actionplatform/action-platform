import { SessionsCard, TokensCard } from "@/features/account";
import { ApiCard } from "@/features/organization";
import { API_BASE, api } from "@/lib/api";
import { tokensOfUser } from "@/lib/api-tokens";
import { requireOrg } from "@/lib/session";
import { sessionsOf } from "@/lib/sessions";
import { v1 } from "@/lib/v1";

const DOCS_URL = "https://github.com/actionplatform/action-platform/blob/master/docs/use_api.md";

export const dynamic = "force-dynamic";

export default async function SessionsPage() {
  await requireOrg();
  const [tokens, sessions, access] = await Promise.all([tokensOfUser(), sessionsOf(), v1.access()]);
  const now = Date.now();

  let version: string | null = null;
  try {
    version = (await api.version()).version;
  } catch {}

  return (
    <div className="space-y-5">
      <TokensCard tokens={tokens} now={now} scopes={access.scopes} />
      <SessionsCard sessions={sessions} now={now} />
      <ApiCard baseUrl={API_BASE} version={version} docsUrl={DOCS_URL} />
    </div>
  );
}
