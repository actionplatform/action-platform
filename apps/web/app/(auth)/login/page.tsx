import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import { setupStatus } from "@/lib/setup";
import { LoginForm } from "./login-form";

export default async function LoginPage() {
  const status = await setupStatus();
  if (!status.complete) redirect("/setup");
  if (await getSession()) redirect("/projects");

  return <LoginForm />;
}
