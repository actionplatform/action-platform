import { KeyRound } from "lucide-react";
import Link from "next/link";
import { API_BASE, api } from "@/lib/api";
import { requireOrg } from "@/lib/session";
import { ApiCard } from "../api-card";

const DOCS_URL = "https://github.com/actionplatform/action-platform/blob/master/docs/use_api.md";

export const dynamic = "force-dynamic";

export default async function DevelopersSettingsPage() {
  await requireOrg();

  let version: string | null = null;
  try {
    version = (await api.version()).version;
  } catch {}

  return (
    <div className="space-y-5">
      <ApiCard baseUrl={API_BASE} version={version} docsUrl={DOCS_URL} />
      <Link href="/account" className="flex items-center gap-3 rounded-[11px] border border-border px-6 py-4 text-sm transition-colors hover:border-border-hover hover:bg-surface-hover">
        <KeyRound className="size-4 text-secondary" strokeWidth={1.75} />
        <span><span className="font-medium">API tokens</span> <span className="text-secondary">— personal tokens for the CLI and MCP servers live under your account.</span></span>
      </Link>
    </div>
  );
}
