import { headers } from "next/headers";
import { invitationsOf, membersOf } from "@/lib/orgs";
import { publicOrigin } from "@/lib/origin";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";
import { MembersPanel } from "../members-panel";
import { RolesCard } from "../roles-card";

export const dynamic = "force-dynamic";

export default async function MembersSettingsPage() {
  const { session, org } = await requireOrg();
  const canManage = !!session.grants["org.manage"];
  const [members, invitations, catalog] = await Promise.all([membersOf(), canManage ? invitationsOf() : Promise.resolve([]), v1.access()]);
  const origin = publicOrigin(await headers());

  return (
    <div className="space-y-5">
      <MembersPanel
        roles={catalog.roles}
        org={{ name: org.name, slug: org.slug }}
        members={members.map((m) => ({ id: m.id, userId: m.userId, name: m.name, email: m.email, role: m.role }))}
        invitations={invitations.map((i) => ({ id: i.id, email: i.email, role: i.role, inviter: i.inviter, expiresAt: i.expiresAt.toISOString() }))}
        me={session.user.id}
        canManage={canManage}
        origin={origin}
      />
      <RolesCard access={catalog} />
    </div>
  );
}
