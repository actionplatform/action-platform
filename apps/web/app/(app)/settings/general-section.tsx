import { Panel, PanelHeader } from "@/components/ui/panel";
import { api } from "@/lib/api";
import { v1 } from "@/lib/v1";
import { gitAuthorOf } from "@/lib/org-settings";
import { requireOrg } from "@/lib/session";
import { DeleteOrganizationCard, GitflowCard, IdentityCard } from "@/features/organization";
import { ProtectionDefaultCard } from "@/features/protection";
import { protectionDefaultOf } from "@/lib/protection";

export async function GeneralSection() {
  const { session, org } = await requireOrg();
  const canManage = !!session.grants["org.manage"];
  const [author, projects] = await Promise.all([gitAuthorOf(), v1.projects(org.id).catch(() => [])]);

  return (
    <div className="space-y-5">
      <Panel>
        <PanelHeader title="Organization" />
        <dl className="grid grid-cols-1 gap-4 p-4 text-sm sm:grid-cols-2">
          <div><dt className="text-xs text-secondary">Name</dt><dd className="mt-0.5 font-medium">{org.name}</dd></div>
          <div><dt className="text-xs text-secondary">Slug</dt><dd className="mt-0.5 font-mono">{org.slug}</dd></div>
          <div><dt className="text-xs text-secondary">Your role</dt><dd className="mt-0.5">{session.role}</dd></div>
        </dl>
      </Panel>
      <IdentityCard author={author} canManage={canManage} />
      <DeleteOrganizationCard slug={org.slug} name={org.name} isOwner={session.role === "owner"} projects={projects.length} apps={projects.reduce((n, p) => n + (p.apps?.length ?? 0), 0)} />
    </div>
  );
}

export async function GitRulesSection() {
  const { session } = await requireOrg();
  const canManage = !!session.grants["org.manage"];
  const protectionDefault = await protectionDefaultOf();
  let rules: { kinds: string[]; protected: string[]; types: string[] } | null = null;
  try {
    rules = await api.gitflowRules();
  } catch {}

  return (
    <div className="space-y-5">
      <GitflowCard rules={rules} />
      <ProtectionDefaultCard initial={protectionDefault} canManage={canManage} />
    </div>
  );
}
