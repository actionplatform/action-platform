import { InstanceView } from "@/features/instance";
import { v1 } from "@/lib/v1";

export async function InstanceSection() {
  let health: Awaited<ReturnType<typeof v1.instanceHealth>> | null = null;
  let error: string | null = null;
  try {
    health = await v1.instanceHealth();
  } catch (e) {
    error = e instanceof Error ? e.message : "The instance health could not be read.";
  }

  return (
    <div>
      {health ? <InstanceView health={health} /> : <div className="rounded-md border border-status-bad/30 bg-status-bad/5 px-3 py-2 text-[13px] text-status-bad">{error}</div>}
    </div>
  );
}
