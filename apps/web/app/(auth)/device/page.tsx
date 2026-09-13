import { requireSession } from "@/lib/session";
import { DeviceApprove } from "./approve";

export default async function DevicePage({ searchParams }: { searchParams: Promise<{ user_code?: string }> }) {
  await requireSession();
  const { user_code } = await searchParams;

  return <DeviceApprove initialCode={(user_code ?? "").toUpperCase()} />;
}
