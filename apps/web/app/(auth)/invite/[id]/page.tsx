import { redirect } from "next/navigation";
import { Logo } from "@/components/logo";
import { Card, CardContent } from "@/components/ui/card";
import { invitationById } from "@/lib/orgs";
import { getSession } from "@/lib/session";
import { setupStatus } from "@/lib/setup";
import { InviteForm } from "./invite-form";

export const dynamic = "force-dynamic";

export default async function InvitePage({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ error?: string }> }) {
  const status = await setupStatus();
  if (!status.complete) redirect("/setup");
  const { id } = await params;
  const invitation = await invitationById(id);

  if (!invitation || invitation.status !== "pending" || invitation.expired) {
    return (
      <Card className="w-full max-w-sm">
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2 font-semibold"><Logo className="size-5" /> action-platform</div>
          <h1 className="text-lg font-semibold">Invitation {invitation ? (invitation.expired ? "expired" : invitation.status) : "not found"}</h1>
          <p className="text-sm text-secondary">Ask an owner or admin of the organization for a new link.</p>
        </CardContent>
      </Card>
    );
  }

  const session = await getSession();
  const { error } = await searchParams;
  const mode = !session ? "join" : invitation.login ? "verify" : session.user.email.toLowerCase() === invitation.email ? "accept" : "mismatch";

  return <InviteForm invitation={{ id: invitation.id, email: invitation.email, login: invitation.login, host: invitation.hostKind, role: invitation.role, org: invitation.org.name, inviter: invitation.inviter }} mode={mode} currentEmail={session?.user.email ?? null} google={status.google} problem={error ?? null} />;
}
