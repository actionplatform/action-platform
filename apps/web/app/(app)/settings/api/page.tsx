import { API_BASE, api } from "@/lib/api";
import { requireOrg } from "@/lib/session";
import { ApiCard } from "../api-card";

const DOCS_URL = "https://github.com/actionplatform/action-platform/blob/master/docs/use_api.md";

export const dynamic = "force-dynamic";

export default async function ApiSettingsPage() {
  await requireOrg();

  let version: string | null = null;
  try {
    version = (await api.version()).version;
  } catch {}

  return <ApiCard baseUrl={API_BASE} version={version} docsUrl={DOCS_URL} />;
}
