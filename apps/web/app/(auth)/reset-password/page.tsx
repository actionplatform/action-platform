import { redirect } from "next/navigation";
import { setupStatus } from "@/lib/setup";
import { ResetPasswordForm } from "./reset-password-form";

export default async function ResetPasswordPage({ searchParams }: { searchParams: Promise<{ token?: string }> }) {
  const status = await setupStatus();
  if (!status.complete) redirect("/setup");
  const { token } = await searchParams;
  if (!token) redirect("/forgot-password");

  return <ResetPasswordForm token={token} />;
}
