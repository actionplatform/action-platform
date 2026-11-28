import { headers } from "next/headers";
import { invitationsOf, membersPageOf } from "@/lib/orgs";
import { pageQuery } from "@/lib/page";
import { publicOrigin } from "@/lib/origin";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";
import { MembersPanel } from "@/features/organization";
import { RolesCard } from "@/features/organization";

export const dynamic = "force-dynamic";

export default async function MembersSettingsPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { session, org } = await requireOrg();
  const canManage = !!session.grants["org.manage"];
  const query = pageQuery(await searchParams, "members");
  const [members, invitations, catalog] = await Promise.all([membersPageOf(query), canManage ? invitationsOf() : Promise.resolve([]), v1.access()]);
  const origin = publicOrigin(await headers());

  return (
    <div className="space-y-5">
      <MembersPanel
        roles={catalog.roles}
        org={{ name: org.name, slug: org.slug }}
        paging={{ total: members.total, page: members.page, per: members.per }}
        members={members.items.map((m) => ({ id: m.id, userId: m.userId, name: m.name, email: m.email, role: m.role }))}
        invitations={invitations.map((i) => ({ id: i.id, email: i.email, login: i.login, teams: i.teams, role: i.role, inviter: i.inviter, expiresAt: i.expiresAt.toISOString(), emailState: i.emailState, emailError: i.emailError }))}
        me={session.user.id}
        canManage={canManage}
        origin={origin}
      />
      <RolesCard access={catalog} />
    </div>
  );
}
