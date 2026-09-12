import { Plus } from "lucide-react";
import Link from "next/link";
import { ApiOffline } from "@/components/api-offline";
import { PageHeader } from "@/components/layout/page";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Table, Td, Th } from "@/components/ui/table";
import { api, type ProjectRow } from "@/lib/api";
import { addProject } from "./actions";
import { RemoveButton } from "./remove-button";

export default async function ProjectsPage() {
  let rows: ProjectRow[];
  try {
    rows = await api.projects.list();
  } catch (e) {
    return <ApiOffline error={e} />;
  }

  return (
    <>
      <PageHeader title="Projects" description="Local checkouts the API knows about. Register one by path." />

      <form action={addProject} className="flex gap-2 mb-6">
        <input
          name="path"
          placeholder="/path/to/project (must contain platform.toml)"
          className="flex-1 h-9 rounded-md border border-border bg-card px-3 text-sm font-mono"
          required
        />
        <Button type="submit"><Plus className="size-4" /> Add</Button>
      </form>

      <Card>
        <Table>
          <thead>
            <tr><Th>name</Th><Th>type</Th><Th>language</Th><Th>branch</Th><Th>version</Th><Th>path</Th><Th /></tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><Td colSpan={7} className="text-muted-foreground text-center py-8">No projects yet.</Td></tr>
            )}
            {rows.map((p) => (
              <tr key={p.id} className="hover:bg-muted/50">
                <Td>
                  <Link href={`/projects/${p.id}`} className="font-medium hover:underline">{p.name}</Link>
                  {!p.exists && <Badge tone="bad" className="ml-2">missing</Badge>}
                </Td>
                <Td>{p.type ?? "—"}</Td>
                <Td>{p.language ?? "—"}</Td>
                <Td><code className="font-mono text-xs">{p.branch ?? "—"}</code></Td>
                <Td>{p.last_version ?? "—"}</Td>
                <Td className="text-muted-foreground font-mono text-xs">{p.path}</Td>
                <Td className="text-right"><RemoveButton id={p.id} /></Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </>
  );
}
