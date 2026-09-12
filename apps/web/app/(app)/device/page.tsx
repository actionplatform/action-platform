import { PageHeader } from "@/components/layout/page";
import { requireSession } from "@/lib/session";
import { DeviceApprove } from "./approve";

// Where `action-platform login` sends the browser. Behind the sidebar so
// the user is signed in before approving.
export default async function DevicePage({ searchParams }: { searchParams: Promise<{ user_code?: string }> }) {
  await requireSession();
  const { user_code } = await searchParams;

  return (
    <>
      <PageHeader title="Authorize a device" description="A CLI or MCP server is asking to act as you. Check the code matches what the terminal shows." />
      <DeviceApprove initialCode={user_code ?? ""} />
    </>
  );
}
