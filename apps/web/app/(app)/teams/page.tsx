import { PageHeader } from "@/components/layout/page";
import { roleOf } from "@/lib/orgs";
import { can } from "@/lib/permissions";
import { requireOrg } from "@/lib/session";
import { teamsOf } from "@/lib/teams";
import { NewTeamButton, TeamsView } from "./teams-view";

export const dynamic = "force-dynamic";

export default async function TeamsPage() {
  const { session, org } = await requireOrg();
  const [teams, role] = await Promise.all([teamsOf(org.id), roleOf(session.user.id, org.id)]);
  const canManage = can(role, "org.manage");

  return (
    <>
      <PageHeader title="Teams" description={`Groups of ${org.name} members and the projects they look after.`} actions={canManage ? <NewTeamButton /> : undefined} />
      <TeamsView teams={teams.map((t) => ({ id: t.id, name: t.name, slug: t.slug, description: t.description, members: t.members, projects: t.projects }))} canManage={canManage} />
    </>
  );
}
