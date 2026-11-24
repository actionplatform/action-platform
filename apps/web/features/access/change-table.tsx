import { Badge } from "@/components/ui/badge";
import type { AccessChange } from "@/lib/v1";

const TONE = { planned: "neutral", applied: "success", refused: "danger", failed: "danger" } as const;

export function ChangeTable({ changes }: { changes: AccessChange[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-[13px]">
        <thead className="text-xs text-secondary">
          <tr className="border-b border-border">
            <th className="px-4 py-2 font-medium">Change</th>
            <th className="px-4 py-2 font-medium">Account</th>
            <th className="px-4 py-2 font-medium">Resource</th>
            <th className="px-4 py-2 font-medium">Level</th>
            <th className="px-4 py-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {changes.map((c, i) => (
            <tr key={`${c.service}:${c.account}:${c.resource}:${i}`} className={c.status === "refused" ? "border-b border-status-bad/30 bg-status-bad/5 last:border-0" : "border-b border-border last:border-0"}>
              <td className="px-4 py-2 capitalize">{c.action}</td>
              <td className="px-4 py-2 font-mono">{c.account}</td>
              <td className="px-4 py-2 font-mono">{c.service}/{c.resource}</td>
              <td className="px-4 py-2 font-mono">{c.previous ? `${c.previous} → ${c.level}` : c.level}</td>
              <td className="px-4 py-2">
                <Badge tone={TONE[c.status]}>{c.status}</Badge>
                {c.detail && <div className={c.status === "refused" || c.status === "failed" ? "mt-1 text-status-bad" : "mt-1 text-secondary"}>{c.detail}</div>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
