import { api } from "@/lib/api";
import { requireOrg } from "@/lib/session";
import { GitflowCard } from "../gitflow-card";

export const dynamic = "force-dynamic";

export default async function GitflowSettingsPage() {
  await requireOrg();

  let rules: { kinds: string[]; protected: string[]; types: string[] } | null = null;
  try {
    rules = await api.gitflowRules();
  } catch {}

  return <GitflowCard rules={rules} />;
}
