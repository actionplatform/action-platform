export type EmailBadge = { label: string; tone: "success" | "warning" | "neutral"; reason: string | null };

export function invitationEmail(state: string, error: string | null): EmailBadge | null {
  if (state === "sent") return { label: "Sent", tone: "success", reason: null };
  if (state === "failed") return { label: "Not sent", tone: "warning", reason: error ?? "the mail server refused it" };
  if (state === "not_sent") return { label: "Not sent", tone: "neutral", reason: null };
  return null;
}

export function invitationEmailNotice(state: string, error: string | null, email: string): string | null {
  if (state === "sent") return `An email with the link went to ${email}.`;
  if (state === "failed") return `The email could not be sent (${error ?? "the mail server refused it"}). Share the link by hand or resend it from the list.`;
  return null;
}
