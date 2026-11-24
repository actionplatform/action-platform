import type { InstanceHealthRow } from "@/lib/v1";

export function ageText(seconds: number | null | undefined): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  return `${Math.floor(seconds / 86400)}d`;
}

export function problems(h: InstanceHealthRow): string[] {
  const out: string[] = [];
  if (!h.database) out.push("The database does not answer.");
  else if (!h.migrations) out.push("The database is behind the API: run the migrations.");
  for (const [group, alive] of Object.entries(h.workers)) {
    if (!alive && h.database && h.migrations) out.push(`No worker is running for ${group} jobs.`);
  }
  for (const row of h.queue) {
    if (row.queued > 0 && !row.worker_running && !out.some((p) => p.includes(` ${row.group} jobs`))) out.push(`${row.queued} ${row.kind} job${row.queued === 1 ? "" : "s"} waiting and no worker takes ${row.kind} jobs.`);
  }
  const failure = h.integrations.smtp.last_failure;
  if (failure) out.push(`The last ${failure.what} email failed: ${failure.error}`);
  return out;
}
