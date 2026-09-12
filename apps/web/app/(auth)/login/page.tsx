import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import { setupStatus } from "@/lib/setup";
import { LoginForm } from "./login-form";

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string }> }) {
  const status = await setupStatus();
  if (!status.complete) redirect("/setup");
  const { next } = await searchParams;
  const target = next && next.startsWith("/") ? next : "/projects";
  if (await getSession()) redirect(target);

  return <LoginForm next={target} />;
}
