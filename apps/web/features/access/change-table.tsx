import { Badge } from "@/components/ui/badge";
import { TBody, Td, Th, Tr } from "@/components/ui/table";
import type { AccessChange } from "@/lib/v1";

const TONE = { planned: "neutral", applied: "success", refused: "danger", failed: "danger" } as const;

export function ChangeTable({ changes }: { changes: AccessChange[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-[13px]">
        <thead>
          <tr>
            <Th>Change</Th>
            <Th>Account</Th>
            <Th>Resource</Th>
            <Th>Level</Th>
            <Th>Status</Th>
          </tr>
        </thead>
        <TBody>
          {changes.map((c, i) => (
            <Tr key={`${c.service}:${c.account}:${c.resource}:${i}`} className={c.status === "refused" ? "bg-status-bad/5" : undefined}>
              <Td className="whitespace-nowrap capitalize">{c.action}</Td>
              <Td className="font-mono [overflow-wrap:anywhere]">{c.account}</Td>
              <Td className="font-mono [overflow-wrap:anywhere]">{c.service}/{c.resource}</Td>
              <Td className="whitespace-nowrap font-mono">{c.previous ? `${c.previous} → ${c.level}` : c.level}</Td>
              <Td>
                <Badge tone={TONE[c.status]}>{c.status}</Badge>
                {c.detail && <div className={c.status === "refused" || c.status === "failed" ? "mt-1 text-status-bad" : "mt-1 text-secondary"}>{c.detail}</div>}
              </Td>
            </Tr>
          ))}
        </TBody>
      </table>
    </div>
  );
}
