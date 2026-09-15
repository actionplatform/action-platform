import { Card } from "@/components/ui/card";
import { gitAuthorOf } from "@/lib/org-settings";
import { requireOrg } from "@/lib/session";
import { IdentityCard } from "./identity-card";

export const dynamic = "force-dynamic";

export default async function GeneralSettingsPage() {
  const { session, org } = await requireOrg();
  const canManage = !!session.grants["org.manage"];
  const author = await gitAuthorOf();

  return (
    <div className="space-y-5">
      <Card className="rounded-[11px]">
        <header className="border-b border-border px-6 py-4"><h2 className="text-[18px] font-semibold">Organization</h2></header>
        <dl className="grid grid-cols-1 gap-4 px-6 py-4 text-sm sm:grid-cols-2">
          <div><dt className="text-xs text-secondary">Name</dt><dd className="mt-0.5 font-medium">{org.name}</dd></div>
          <div><dt className="text-xs text-secondary">Slug</dt><dd className="mt-0.5 font-mono">{org.slug}</dd></div>
          <div><dt className="text-xs text-secondary">Your role</dt><dd className="mt-0.5">{session.role}</dd></div>
        </dl>
      </Card>
      <IdentityCard author={author} canManage={canManage} />
    </div>
  );
}
