import { Badge } from "@/components/ui/badge";
import { Cell } from "@/components/ui/data-table";
import { TBody, Table, Td, Th, Tr } from "@/components/ui/table";
import type { AccessChange } from "@/lib/v1";

const TONE = { planned: "neutral", applied: "success", refused: "danger", failed: "danger" } as const;

export function ChangeTable({ changes }: { changes: AccessChange[] }) {
  return (
    <Table className="text-[13px]" columns={[{ width: 12 }, { width: 22 }, { width: 26 }, { width: 14 }, { width: 26 }]}>
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
              <Td className="capitalize"><Cell>{c.action}</Cell></Td>
              <Td><Cell mono>{c.account}</Cell></Td>
              <Td><Cell mono>{c.service}/{c.resource}</Cell></Td>
              <Td><Cell mono>{c.previous ? `${c.previous} → ${c.level}` : c.level}</Cell></Td>
              <Td>
                <Cell title={c.detail ? `${c.status}: ${c.detail}` : c.status}>
                  <Badge tone={TONE[c.status]}>{c.status}</Badge>
                  {c.detail && <span className={c.status === "refused" || c.status === "failed" ? "ml-2 text-status-bad" : "ml-2 text-secondary"}>{c.detail}</span>}
                </Cell>
              </Td>
            </Tr>
          ))}
        </TBody>
    </Table>
  );
}
