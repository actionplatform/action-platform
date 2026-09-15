import { requireOrg } from "@/lib/session";
import { teamsOf } from "@/lib/teams";
import { NewTeamButton, TeamsView } from "@/features/organization";

export const dynamic = "force-dynamic";

export default async function TeamsPage() {
  const { session, org } = await requireOrg();
  const teams = await teamsOf(org.id);
  const canManage = !!session.grants["org.manage"];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-secondary">Groups of {org.name} members and the projects they look after.</p>
        {canManage && <NewTeamButton />}
      </div>
      <TeamsView teams={teams.map((t) => ({ id: t.id, name: t.name, slug: t.slug, description: t.description, members: t.members, projects: t.projects }))} canManage={canManage} />
    </div>
  );
}
