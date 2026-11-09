import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import { setupStatus } from "@/lib/setup";
import { ForgotPasswordForm } from "./forgot-password-form";

export default async function ForgotPasswordPage() {
  const status = await setupStatus();
  if (!status.complete) redirect("/setup");
  if (await getSession()) redirect("/projects");
  if (!status.passwordRecovery) redirect("/login");

  return <ForgotPasswordForm />;
}
