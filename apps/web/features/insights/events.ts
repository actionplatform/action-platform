import type { DashboardEvent } from "@/lib/insights";

export type EventGroup = { event: DashboardEvent; count: number };

export function grouped(events: DashboardEvent[]): EventGroup[] {
  const out: EventGroup[] = [];
  for (const e of events) {
    const last = out[out.length - 1];
    if (last && last.event.kind === e.kind && last.event.app_id === e.app_id && last.event.title === e.title && last.event.status === e.status) last.count += 1;
    else out.push({ event: e, count: 1 });
  }
  return out;
}
