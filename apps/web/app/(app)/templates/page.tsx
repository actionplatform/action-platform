import { ApiOffline } from "@/components/api-offline";
import { PageHeader } from "@/components/layout/page";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Td, Th } from "@/components/ui/table";
import { api, type Matrix } from "@/lib/api";

export default async function TemplatesPage() {
  let m: Matrix;
  try {
    m = await api.matrix();
  } catch (e) {
    return <ApiOffline error={e} />;
  }

  return (
    <>
      <PageHeader title="Templates" description="What action-platform init can generate: projects, cloud overlays, services." />

      <div className="space-y-4">
        <Card>
          <CardHeader><CardTitle>Projects</CardTitle><Badge>{m.projects.length}</Badge></CardHeader>
          <Table>
            <thead><tr><Th>type</Th><Th>stack</Th><Th>template</Th><Th>description</Th></tr></thead>
            <tbody>
              {m.projects.map((p) => (
                <tr key={`${p.type}/${p.stack}/${p.template}`}>
                  <Td>{p.type}</Td><Td>{p.stack}</Td>
                  <Td className="font-mono text-xs">{p.template}{p.default && <Badge tone="ok" className="ml-2">default</Badge>}</Td>
                  <Td className="text-muted-foreground">{p.description}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>

        <Card>
          <CardHeader><CardTitle>Clouds</CardTitle><Badge>{m.clouds.length}</Badge></CardHeader>
          <Table>
            <thead><tr><Th>name</Th><Th>types</Th><Th>languages</Th><Th>description</Th></tr></thead>
            <tbody>
              {m.clouds.map((c) => (
                <tr key={c.name}>
                  <Td className="font-mono text-xs">{c.name}</Td><Td>{c.types.join(", ")}</Td><Td>{c.languages.join(", ")}</Td>
                  <Td className="text-muted-foreground">{c.description}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>

        <Card>
          <CardHeader><CardTitle>Services</CardTitle><Badge>{m.services.length}</Badge></CardHeader>
          <Table>
            <thead><tr><Th>name</Th><Th>providers</Th><Th>description</Th></tr></thead>
            <tbody>
              {m.services.map((s) => (
                <tr key={s.name}>
                  <Td className="font-mono text-xs">{s.name}</Td><Td>{s.providers.join(", ")}</Td>
                  <Td className="text-muted-foreground">{s.description}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
      </div>
    </>
  );
}
